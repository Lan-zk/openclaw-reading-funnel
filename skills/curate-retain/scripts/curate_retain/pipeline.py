"""Pipeline entrypoint for curate-retain."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from .io_utils import (
    add_days,
    extract_source_name,
    generate_run_id,
    iso_now,
    load_daily_review_issues,
    load_human_decisions,
    load_json_array,
    make_failure_id,
    make_knowledge_asset_id,
    make_preference_signal_id,
    make_queue_item_id,
    make_retention_decision_id,
    normalize_url,
    prepare_output_directory,
    slugify,
    write_json,
    write_text,
)
from .reporting import StepRecorder, build_curation_report, determine_step_status, render_curation_report


PRIORITY_WEIGHT = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
TOPIC_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "this",
    "that",
    "guide",
    "practical",
    "worth",
    "retaining",
    "reference",
    "pattern",
}

REASON_TO_ASSET_TYPE = {
    "LONG_TERM_REFERENCE": "REFERENCE_NOTE",
    "HIGH_INFORMATION_DENSITY": "REFERENCE_NOTE",
    "ACTIONABLE_PRACTICE": "PATTERN",
    "IMPLEMENTATION_PATTERN": "PATTERN",
    "REUSABLE_FRAMEWORK": "PATTERN",
    "STRATEGIC_SIGNAL": "DECISION_INPUT",
    "DECISION_INPUT": "DECISION_INPUT",
}


def build_read_queue(
    digest_candidates: list[dict[str, Any]],
    daily_review_issues: list[dict[str, Any]] | None,
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_source_ids = _collect_daily_review_source_ids(daily_review_issues or [])
    candidate_score_by_id = _candidate_score_by_id(digest_candidates)
    queue_items: list[dict[str, Any]] = []
    for candidate in digest_candidates:
        if candidate.get("digest_status") == "FILTERED":
            continue
        target_id = candidate["digest_candidate_id"]
        queue_reason: list[str] = []
        if target_id in review_source_ids:
            queue_reason.append("EDITORIAL_PRIORITY")
        if float(candidate.get("digest_score") or 0.0) >= 0.85:
            queue_reason.append("HIGH_DIGEST_SCORE")
        if float(candidate.get("quality_score") or 0.0) >= 0.8:
            queue_reason.append("POSSIBLE_LONG_TERM_VALUE")
        if candidate.get("needs_review"):
            queue_reason.append("MANUAL_RECHECK")
        if "pattern" in (candidate.get("display_title") or "").lower():
            queue_reason.append("IMPLEMENTATION_RELEVANCE")
        if not queue_reason:
            queue_reason.append("POSSIBLE_LONG_TERM_VALUE")
        queue_items.append(
            {
                "queue_item_id": make_queue_item_id("DIGEST_CANDIDATE", target_id),
                "target_type": "DIGEST_CANDIDATE",
                "target_id": target_id,
                "source_digest_candidate_ids": [target_id],
                "queue_reason": sorted(set(queue_reason)),
                "queue_priority": _queue_priority_for_candidate(candidate, review_source_ids),
                "run_id": run_id,
            }
        )
    queue_items.sort(
        key=lambda item: (
            PRIORITY_WEIGHT[item["queue_priority"]],
            candidate_score_by_id.get(item["target_id"], 0.0),
            item["target_id"],
        ),
        reverse=True,
    )
    return queue_items, []


def capture_human_decision(
    read_queue_items: list[dict[str, Any]],
    human_decisions: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    del run_id
    queue_by_target = {item["target_id"]: item for item in read_queue_items}
    decision_drafts: list[dict[str, Any]] = []
    for item in human_decisions:
        queue_item = queue_by_target.get(item["target_id"])
        decision_drafts.append(
            {
                "target_type": item["target_type"],
                "target_id": item["target_id"],
                "decision": item["decision"],
                "confidence": _as_float(item.get("confidence")),
                "reason_tags": list(item.get("reason_tags", [])),
                "reason_text": item.get("reason_text"),
                "decision_by": item["decision_by"],
                "decision_at": item["decision_at"],
                "source_queue_item_id": queue_item["queue_item_id"] if queue_item else None,
            }
        )
    return decision_drafts, []


def persist_retention_decision(
    human_decision_drafts: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    for draft in human_decision_drafts:
        decisions.append(
            {
                "retention_decision_id": make_retention_decision_id(
                    draft["target_type"],
                    draft["target_id"],
                    draft["decision_at"],
                    draft["decision_by"],
                ),
                "target_type": draft["target_type"],
                "target_id": draft["target_id"],
                "decision": draft["decision"],
                "confidence": draft.get("confidence"),
                "reason_tags": list(draft.get("reason_tags", [])),
                "reason_text": draft.get("reason_text"),
                "decision_at": draft["decision_at"],
                "decision_by": draft["decision_by"],
                "run_id": run_id,
            }
        )
    return decisions, []


def derive_long_term_tags(
    retention_decisions: list[dict[str, Any]],
    retained_target_snapshots: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    snapshots_by_target = {item["target_id"]: item for item in retained_target_snapshots}
    drafts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for decision in retention_decisions:
        if decision["decision"] != "KEEP":
            continue
        snapshot = snapshots_by_target.get(decision["target_id"])
        if snapshot is None:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="derive_long_term_tags",
                    scope_type="SNAPSHOT",
                    scope_id=decision["target_id"],
                    failure_type="SNAPSHOT_BUILD_ERROR",
                    message="missing retained target snapshot",
                    details={"target_id": decision["target_id"]},
                    retryable=False,
                )
            )
            continue
        drafts.append(
            {
                "origin_retention_decision_id": decision["retention_decision_id"],
                "target_type": decision["target_type"],
                "target_id": decision["target_id"],
                "title": snapshot.get("title"),
                "summary": snapshot.get("summary"),
                "canonical_url": snapshot.get("canonical_url"),
                "topic_tags": _topic_tags(snapshot, decision),
                "asset_type": _asset_type_for_decision(decision),
                "long_term_value_reason": decision.get("reason_text") or _reason_from_tags(decision.get("reason_tags", [])),
                "run_id": run_id,
            }
        )
    return drafts, failures


def store_knowledge_asset(
    knowledge_asset_drafts: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assets: list[dict[str, Any]] = []
    for draft in knowledge_asset_drafts:
        assets.append(
            {
                "knowledge_asset_id": make_knowledge_asset_id(
                    draft["origin_retention_decision_id"],
                    draft.get("title"),
                ),
                "origin_retention_decision_id": draft["origin_retention_decision_id"],
                "title": draft.get("title"),
                "summary": draft.get("summary"),
                "canonical_url": draft.get("canonical_url"),
                "topic_tags": list(draft.get("topic_tags", [])),
                "asset_type": draft["asset_type"],
                "long_term_value_reason": draft.get("long_term_value_reason"),
                "stored_at": iso_now(),
                "asset_status": "STORED",
                "run_id": run_id,
            }
        )
    return assets, []


def derive_preference_signals(
    retention_decisions: list[dict[str, Any]],
    knowledge_assets: list[dict[str, Any]] | None,
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assets_by_origin = {
        item["origin_retention_decision_id"]: item for item in (knowledge_assets or [])
    }
    signals: list[dict[str, Any]] = []
    for decision in retention_decisions:
        if decision["decision"] == "KEEP":
            asset = assets_by_origin.get(decision["retention_decision_id"])
            topic_tags = list(asset.get("topic_tags", [])) if asset else []
            for topic_tag in topic_tags:
                signals.append(
                    _build_signal(
                        signal_type="TOPIC_PREFERENCE",
                        signal_value=topic_tag,
                        decision=decision,
                        asset=asset,
                        weight=_signal_weight(decision, 0.0),
                        expires_at=add_days(decision.get("decision_at"), 90),
                        run_id=run_id,
                    )
                )
            if asset and asset.get("canonical_url"):
                source_name = extract_source_name(asset["canonical_url"])
                if source_name:
                    signals.append(
                        _build_signal(
                            signal_type="SOURCE_PREFERENCE",
                            signal_value=source_name,
                            decision=decision,
                            asset=asset,
                            weight=_signal_weight(decision, -0.1),
                            expires_at=add_days(decision.get("decision_at"), 60),
                            run_id=run_id,
                        )
                    )
        elif decision["decision"] == "DROP":
            negative_value = next(iter(decision.get("reason_tags", []) or []), "drop")
            signals.append(
                _build_signal(
                    signal_type="NEGATIVE_SIGNAL",
                    signal_value=negative_value,
                    decision=decision,
                    asset=None,
                    weight=_signal_weight(decision, 0.0),
                    expires_at=add_days(decision.get("decision_at"), 45),
                    run_id=run_id,
                )
            )
    return signals, []


def run_pipeline(
    digest_candidates_path: str,
    output_root: str,
    daily_review_issue_path: str | None = None,
    human_decisions_path: str | None = None,
    run_id: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    mode: str = "NORMAL",
) -> dict[str, Any]:
    del runtime_overrides
    del mode
    resolved_run_id = run_id or generate_run_id()
    try:
        digest_candidates = load_json_array(digest_candidates_path)
        daily_review_issues = load_daily_review_issues(daily_review_issue_path)
        human_decisions = load_human_decisions(human_decisions_path)
        run_dir = prepare_output_directory(output_root, resolved_run_id)
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": {}}

    workflow_started_at = iso_now()
    recorder = StepRecorder(run_id=resolved_run_id, started_at=workflow_started_at)
    all_failures: list[dict[str, Any]] = []
    artifact_paths = {
        "retention_decisions": str(run_dir / "retention-decisions.json"),
        "read_queue": str(run_dir / "read-queue.json"),
        "knowledge_assets": str(run_dir / "knowledge-assets.json"),
        "preference_signals": str(run_dir / "preference-signals.json"),
        "curation_failures": str(run_dir / "curation-failures.json"),
        "step_manifest": str(run_dir / "step-manifest.json"),
        "curation_report": str(run_dir / "curation-report.md"),
    }
    metrics: dict[str, Any] = {
        "digest_candidate_input_count": len(digest_candidates),
        "read_queue_item_count": 0,
        "human_decision_draft_count": 0,
        "retention_decision_count": 0,
        "keep_decision_count": 0,
        "drop_decision_count": 0,
        "defer_decision_count": 0,
        "needs_recheck_decision_count": 0,
        "knowledge_asset_count": 0,
        "preference_signal_count": 0,
        "workflow_duration_ms": 0,
    }

    step_started = iso_now()
    queue_items, failures = build_read_queue(digest_candidates, daily_review_issues, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["read_queue_item_count"] = len(queue_items)
    recorder.record("build_read_queue", determine_step_status(len(queue_items)), len(digest_candidates), len(queue_items), len(queue_items), len(failures), step_started, step_finished)

    step_started = iso_now()
    decision_drafts, failures = capture_human_decision(queue_items, human_decisions, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["human_decision_draft_count"] = len(decision_drafts)
    recorder.record("capture_human_decision", determine_step_status(len(decision_drafts)), len(queue_items), len(decision_drafts), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    decisions, failures = persist_retention_decision(decision_drafts, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["retention_decision_count"] = len(decisions)
    metrics["keep_decision_count"] = sum(1 for item in decisions if item["decision"] == "KEEP")
    metrics["drop_decision_count"] = sum(1 for item in decisions if item["decision"] == "DROP")
    metrics["defer_decision_count"] = sum(1 for item in decisions if item["decision"] == "DEFER")
    metrics["needs_recheck_decision_count"] = sum(1 for item in decisions if item["decision"] == "NEEDS_RECHECK")
    recorder.record("persist_retention_decision", determine_step_status(len(decisions)), len(decision_drafts), len(decisions), 0, len(failures), step_started, step_finished)

    retained_target_snapshots = _build_retained_target_snapshots(decisions, digest_candidates, resolved_run_id)

    step_started = iso_now()
    asset_drafts, failures = derive_long_term_tags(decisions, retained_target_snapshots, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("derive_long_term_tags", determine_step_status(len(asset_drafts)), len(decisions), len(asset_drafts), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    assets, failures = store_knowledge_asset(asset_drafts, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["knowledge_asset_count"] = len(assets)
    recorder.record("store_knowledge_asset", determine_step_status(len(assets)), len(asset_drafts), len(assets), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    signals, failures = derive_preference_signals(decisions, assets, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["preference_signal_count"] = len(signals)
    recorder.record("derive_preference_signals", determine_step_status(len(signals)), len(decisions), len(signals), 0, len(failures), step_started, step_finished)

    workflow_finished_at = iso_now()
    metrics["workflow_duration_ms"] = _duration_ms(workflow_started_at, workflow_finished_at)
    manifest = recorder.build_manifest(workflow_finished_at, all_failures, artifact_paths)
    report = build_curation_report(manifest, queue_items, decisions, assets, signals, all_failures, metrics, workflow_finished_at)

    try:
        write_json(run_dir / "read-queue.json", queue_items)
        write_json(run_dir / "retention-decisions.json", decisions)
        write_json(run_dir / "knowledge-assets.json", assets)
        write_json(run_dir / "preference-signals.json", signals)
        write_json(run_dir / "curation-failures.json", all_failures)
        write_json(run_dir / "step-manifest.json", manifest)
        write_text(run_dir / "curation-report.md", render_curation_report(report))
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": artifact_paths}

    return {
        "run_id": resolved_run_id,
        "workflow_status": manifest["workflow_status"],
        "artifact_paths": artifact_paths,
        "queue_item_count": len(queue_items),
        "retention_decision_count": len(decisions),
        "knowledge_asset_count": len(assets),
        "preference_signal_count": len(signals),
        "failure_record_count": len(all_failures),
    }


def _queue_priority_for_candidate(candidate: dict[str, Any], review_source_ids: set[str]) -> str:
    target_id = candidate["digest_candidate_id"]
    digest_score = float(candidate.get("digest_score") or 0.0)
    if target_id in review_source_ids or digest_score >= 0.85:
        return "HIGH"
    if digest_score >= 0.6 or candidate.get("needs_review"):
        return "MEDIUM"
    return "LOW"


def _candidate_score_by_id(digest_candidates: list[dict[str, Any]]) -> dict[str, float]:
    return {item["digest_candidate_id"]: float(item.get("digest_score") or 0.0) for item in digest_candidates}


def _collect_daily_review_source_ids(daily_review_issues: list[dict[str, Any]]) -> set[str]:
    source_ids: set[str] = set()
    for issue in daily_review_issues:
        source_ids.update(issue.get("source_digest_candidate_ids", []))
        for entries in issue.get("sections", {}).values():
            for entry in entries:
                source_ids.update(entry.get("source_digest_candidate_ids", []))
    return source_ids


def _build_retained_target_snapshots(
    decisions: list[dict[str, Any]],
    digest_candidates: list[dict[str, Any]],
    run_id: str,
) -> list[dict[str, Any]]:
    candidate_by_id = {item["digest_candidate_id"]: item for item in digest_candidates}
    snapshots: list[dict[str, Any]] = []
    for decision in decisions:
        candidate = candidate_by_id.get(decision["target_id"])
        if candidate is None:
            continue
        snapshots.append(
            {
                "target_type": decision["target_type"],
                "target_id": decision["target_id"],
                "title": candidate.get("display_title"),
                "summary": candidate.get("display_summary"),
                "canonical_url": normalize_url(candidate.get("canonical_url")),
                "source_digest_candidate_ids": [candidate["digest_candidate_id"]],
                "snapshot_payload": {
                    "digest_status": candidate.get("digest_status"),
                    "quality_score": candidate.get("quality_score"),
                    "digest_score": candidate.get("digest_score"),
                },
                "run_id": run_id,
            }
        )
    return snapshots


def _topic_tags(snapshot: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    text = " ".join(part for part in [snapshot.get("title") or "", snapshot.get("summary") or ""] if part)
    tags: list[str] = []
    for token in slugify(text).split("-"):
        if len(token) < 4 or token in TOPIC_STOPWORDS:
            continue
        tags.append(token)
        if len(tags) >= 3:
            break
    reason_tags = decision.get("reason_tags", [])
    if "IMPLEMENTATION_PATTERN" in reason_tags and "pattern" not in tags:
        tags.append("pattern")
    if "DECISION_INPUT" in reason_tags and "decision-input" not in tags:
        tags.append("decision-input")
    if not tags:
        tags.append("retained-item")
    return tags[:5]


def _asset_type_for_decision(decision: dict[str, Any]) -> str:
    for reason_tag in decision.get("reason_tags", []):
        if reason_tag in REASON_TO_ASSET_TYPE:
            return REASON_TO_ASSET_TYPE[reason_tag]
    return "WATCH_ITEM"


def _reason_from_tags(reason_tags: list[str]) -> str:
    if not reason_tags:
        return "Marked for long-term retention."
    return "Derived from reason tags: " + ", ".join(reason_tags)


def _signal_weight(decision: dict[str, Any], adjustment: float) -> float:
    base = float(decision.get("confidence") or 0.7) + adjustment
    return round(max(0.3, min(1.0, base)), 4)


def _build_signal(
    signal_type: str,
    signal_value: str,
    decision: dict[str, Any],
    asset: dict[str, Any] | None,
    weight: float,
    expires_at: str,
    run_id: str,
) -> dict[str, Any]:
    derived_from = {
        "origin_retention_decision_id": decision["retention_decision_id"],
        "target_type": decision["target_type"],
        "target_id": decision["target_id"],
        "reason_tags": list(decision.get("reason_tags", [])),
    }
    if asset is not None:
        derived_from["knowledge_asset_id"] = asset["knowledge_asset_id"]
    return {
        "preference_signal_id": make_preference_signal_id(signal_type, signal_value, decision["retention_decision_id"]),
        "signal_type": signal_type,
        "signal_value": signal_value,
        "weight": weight,
        "origin_retention_decision_id": decision["retention_decision_id"],
        "supplementary_knowledge_asset_id": asset["knowledge_asset_id"] if asset is not None else None,
        "derived_from": derived_from,
        "expires_at": expires_at,
        "run_id": run_id,
    }


def _make_failure(
    run_id: str,
    step_name: str,
    scope_type: str,
    scope_id: str | None,
    failure_type: str,
    message: str,
    details: dict[str, Any],
    retryable: bool,
) -> dict[str, Any]:
    return {
        "failure_id": make_failure_id(run_id, step_name, scope_type, scope_id, message),
        "run_id": run_id,
        "step_name": step_name,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "failure_type": failure_type,
        "message": message,
        "details": details,
        "retryable": retryable,
        "recorded_at": iso_now(),
    }


def _duration_ms(started_at: str, finished_at: str) -> int:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if finish.tzinfo is None:
        finish = finish.replace(tzinfo=timezone.utc)
    return max(0, int((finish - start).total_seconds() * 1000))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the curate-retain MVP pipeline.")
    parser.add_argument("--digest-candidates-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--daily-review-issue-path")
    parser.add_argument("--human-decisions-path")
    parser.add_argument("--run-id")
    parser.add_argument("--mode", default="NORMAL")
    args = parser.parse_args(argv)
    result = run_pipeline(
        digest_candidates_path=args.digest_candidates_path,
        output_root=args.output_root,
        daily_review_issue_path=args.daily_review_issue_path,
        human_decisions_path=args.human_decisions_path,
        run_id=args.run_id,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["workflow_status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
