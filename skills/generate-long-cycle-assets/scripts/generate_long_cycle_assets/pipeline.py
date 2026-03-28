"""Pipeline entrypoint for generate-long-cycle-assets."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from .io_utils import (
    ensure_utc_iso,
    generate_run_id,
    iso_now,
    load_json_array,
    make_asset_id,
    make_failure_id,
    make_period_id,
    make_review_item_id,
    make_signal_id,
    make_topic_id,
    prepare_output_directory,
    slugify,
    titleize_token,
    write_json,
    write_text,
)
from .models import (
    AuthorReviewItem,
    HotTopicSignal,
    LongCycleAsset,
    LongCycleFailureRecord,
    LongSignal,
    PeriodAssetSet,
    TopicWritabilityAssessment,
)
from .reporting import (
    StepRecorder,
    build_long_cycle_report,
    determine_step_status,
    render_long_cycle_report,
)


STOPWORDS = {
    "about",
    "after",
    "again",
    "check",
    "daily",
    "early",
    "from",
    "into",
    "note",
    "notes",
    "review",
    "short",
    "team",
    "this",
    "today",
    "update",
    "workflow",
}


def collect_period_assets(
    knowledge_assets: list[dict[str, Any]],
    daily_review_issues: list[dict[str, Any]],
    run_id: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> tuple[PeriodAssetSet, list[LongCycleFailureRecord]]:
    failures: list[LongCycleFailureRecord] = []
    asset_ids = [item["knowledge_asset_id"] for item in knowledge_assets if item.get("knowledge_asset_id")]
    issue_ids = [item["daily_review_issue_id"] for item in daily_review_issues if item.get("daily_review_issue_id")]
    resolved_start = ensure_utc_iso(period_start) or _resolve_period_start(knowledge_assets, daily_review_issues) or iso_now()
    resolved_end = ensure_utc_iso(period_end) or _resolve_period_end(knowledge_assets, daily_review_issues) or iso_now()
    return (
        PeriodAssetSet(
            period_id=make_period_id(resolved_start, resolved_end),
            knowledge_asset_ids=asset_ids,
            daily_review_issue_ids=issue_ids,
            period_start=resolved_start,
            period_end=resolved_end,
            run_id=run_id,
        ),
        failures,
    )


def detect_hot_topics(
    period_asset_set: PeriodAssetSet,
    knowledge_assets: list[dict[str, Any]],
    daily_review_issues: list[dict[str, Any]],
    run_id: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[list[HotTopicSignal], list[LongCycleFailureRecord]]:
    runtime_overrides = runtime_overrides or {}
    topic_sources: dict[str, dict[str, Any]] = defaultdict(lambda: {"asset_ids": set(), "issue_ids": set(), "keywords": set()})
    for asset in knowledge_assets:
        asset_id = asset.get("knowledge_asset_id")
        for token in _tokens_for_asset(asset):
            topic_sources[token]["keywords"].add(token)
            if asset_id:
                topic_sources[token]["asset_ids"].add(asset_id)
    for issue in daily_review_issues:
        issue_id = issue.get("daily_review_issue_id")
        for token in _tokens_for_issue(issue):
            topic_sources[token]["keywords"].add(token)
            if issue_id:
                topic_sources[token]["issue_ids"].add(issue_id)

    hot_topics: list[HotTopicSignal] = []
    failures: list[LongCycleFailureRecord] = []
    for token, payload in sorted(topic_sources.items()):
        asset_count = len(payload["asset_ids"])
        issue_count = len(payload["issue_ids"])
        total_support = asset_count + issue_count
        if total_support == 0:
            continue
        cross_source = 1.0 if asset_count and issue_count else 0.0
        heat_score = min(
            1.0,
            (0.35 * min(asset_count / 2.0, 1.0))
            + (0.30 * min(issue_count / 2.0, 1.0))
            + (0.20 * cross_source)
            + (0.15 * min(total_support / 3.0, 1.0)),
        )
        confidence = min(
            1.0,
            (0.45 * min(total_support / 3.0, 1.0))
            + (0.30 * min(len(token) / 10.0, 1.0))
            + (0.25 * cross_source),
        )
        if heat_score < float(runtime_overrides.get("topic_heat_floor", 0.20)):
            continue
        review_flags: list[str] = []
        if heat_score < float(runtime_overrides.get("hot_topic_selected_threshold", 0.65)):
            review_flags.append("HEAT_BORDERLINE")
        if confidence < float(runtime_overrides.get("topic_confidence_selected_threshold", 0.75)):
            review_flags.append("TOPIC_CONFIDENCE_LOW")
        hot_topics.append(
            HotTopicSignal(
                topic_id=make_topic_id(token),
                supporting_knowledge_asset_ids=sorted(payload["asset_ids"]),
                supporting_issue_ids=sorted(payload["issue_ids"]),
                heat_score=round(heat_score, 4),
                topic_confidence=round(confidence, 4),
                topic_label=titleize_token(token),
                topic_keywords=sorted(payload["keywords"]),
                review_flags=sorted(set(review_flags)),
                run_id=run_id,
            )
        )
    return hot_topics, failures


def identify_long_signals(
    period_asset_set: PeriodAssetSet,
    hot_topics: list[HotTopicSignal],
    knowledge_assets: list[dict[str, Any]],
    daily_review_issues: list[dict[str, Any]],
    run_id: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[list[LongSignal], list[LongCycleFailureRecord]]:
    del period_asset_set
    del daily_review_issues
    runtime_overrides = runtime_overrides or {}
    signals: list[LongSignal] = []
    failures: list[LongCycleFailureRecord] = []
    asset_type_by_id = {item.get("knowledge_asset_id"): item.get("asset_type") for item in knowledge_assets}
    for topic in hot_topics:
        asset_count = len(topic.supporting_knowledge_asset_ids)
        issue_count = len(topic.supporting_issue_ids)
        total_support = asset_count + issue_count
        signal_score = min(
            1.0,
            (0.30 * min(asset_count / 2.0, 1.0))
            + (0.20 * min(issue_count / 2.0, 1.0))
            + (0.30 * topic.heat_score)
            + (0.20 * min(total_support / 4.0, 1.0)),
        )
        if signal_score < float(runtime_overrides.get("long_signal_floor", 0.45)):
            continue
        signal_type = _signal_type_for_topic(topic, asset_type_by_id)
        review_flags = list(topic.review_flags)
        if signal_score < float(runtime_overrides.get("long_signal_selected_threshold", 0.70)):
            review_flags.append("LONG_SIGNAL_BORDERLINE")
        signals.append(
            LongSignal(
                signal_id=make_signal_id(topic.topic_id, signal_type),
                topic_id=topic.topic_id,
                signal_type=signal_type,
                signal_score=round(signal_score, 4),
                supporting_asset_ids=list(topic.supporting_knowledge_asset_ids),
                supporting_issue_ids=list(topic.supporting_issue_ids),
                signal_summary=f"{topic.topic_label} shows repeated long-cycle value across retained assets and daily review material.",
                review_flags=sorted(set(review_flags)),
                run_id=run_id,
            )
        )
    return signals, failures


def compose_weekly_assets(
    period_asset_set: PeriodAssetSet,
    hot_topics: list[HotTopicSignal],
    long_signals: list[LongSignal],
    run_id: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[list[LongCycleAsset], list[AuthorReviewItem], list[LongCycleFailureRecord]]:
    runtime_overrides = runtime_overrides or {}
    assets: list[LongCycleAsset] = []
    review_items: list[AuthorReviewItem] = []
    failures: list[LongCycleFailureRecord] = []
    strong_signals = [item for item in long_signals if item.signal_score >= float(runtime_overrides.get("weekly_signal_threshold", 0.75))]
    if strong_signals:
        selected = sorted(strong_signals, key=lambda item: item.signal_score, reverse=True)[:2]
        theme_ids = [item.topic_id for item in selected]
        asset_status = "READY" if not any(item.review_flags for item in selected) else "NEEDS_AUTHOR_REVIEW"
        assets.append(
            LongCycleAsset(
                long_cycle_asset_id=make_asset_id("WEEKLY", period_asset_set.period_id, run_id),
                asset_scope="WEEKLY",
                title=f"Weekly Focus: {', '.join(_topic_title(topic_id, hot_topics) for topic_id in theme_ids)}",
                summary="A weekly synthesis of the strongest recurring themes from retained knowledge and daily review material.",
                source_knowledge_asset_ids=list(period_asset_set.knowledge_asset_ids),
                source_daily_review_issue_ids=list(period_asset_set.daily_review_issue_ids),
                theme_ids=theme_ids,
                asset_status=asset_status,
                generated_at=iso_now(),
                run_id=run_id,
                writability_score=None,
                structure={
                    "headline": f"Weekly Focus: {', '.join(_topic_title(topic_id, hot_topics) for topic_id in theme_ids)}",
                    "summary": "A weekly synthesis of the strongest recurring themes.",
                    "sections": ["本周主线", "关键资产", "后续可写方向"],
                },
            )
        )
        return assets, review_items, failures

    near_signals = [item for item in long_signals if item.signal_score >= float(runtime_overrides.get("weekly_review_threshold", 0.50))]
    if near_signals:
        top_signal = sorted(near_signals, key=lambda item: item.signal_score, reverse=True)[0]
        review_items.append(
            AuthorReviewItem(
                review_item_id=make_review_item_id("WEEKLY_DRAFT", top_signal.signal_id),
                review_scope="WEEKLY_DRAFT",
                related_object_id=top_signal.signal_id,
                review_flags=sorted(set(top_signal.review_flags or ["WEEKLY_SCOPE_UNCLEAR"])),
                supporting_evidence={
                    "topic_id": top_signal.topic_id,
                    "signal_score": top_signal.signal_score,
                    "supporting_asset_ids": top_signal.supporting_asset_ids,
                    "supporting_issue_ids": top_signal.supporting_issue_ids,
                },
                suggested_action="CLARIFY_THEME",
                run_id=run_id,
            )
        )
        return assets, review_items, failures

    early_topics = [
        item
        for item in hot_topics
        if item.supporting_knowledge_asset_ids
        and not item.supporting_issue_ids
        and item.heat_score >= float(runtime_overrides.get("weekly_early_review_threshold", 0.20))
    ]
    if early_topics:
        top_topic = sorted(early_topics, key=lambda item: item.heat_score, reverse=True)[0]
        review_items.append(
            AuthorReviewItem(
                review_item_id=make_review_item_id("TOPIC_SIGNAL", top_topic.topic_id),
                review_scope="TOPIC_SIGNAL",
                related_object_id=top_topic.topic_id,
                review_flags=sorted(set(top_topic.review_flags or ["EARLY_TOPIC_SIGNAL"])),
                supporting_evidence={
                    "topic_id": top_topic.topic_id,
                    "heat_score": top_topic.heat_score,
                    "supporting_asset_ids": top_topic.supporting_knowledge_asset_ids,
                    "supporting_issue_ids": top_topic.supporting_issue_ids,
                },
                suggested_action="WAIT_FOR_MORE_EVIDENCE",
                run_id=run_id,
            )
        )
    return assets, review_items, failures


def evaluate_topic_writability(
    period_asset_set: PeriodAssetSet,
    hot_topics: list[HotTopicSignal],
    long_signals: list[LongSignal],
    run_id: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[list[TopicWritabilityAssessment], list[LongCycleFailureRecord]]:
    del period_asset_set
    runtime_overrides = runtime_overrides or {}
    hot_topic_by_id = {item.topic_id: item for item in hot_topics}
    assessments: list[TopicWritabilityAssessment] = []
    failures: list[LongCycleFailureRecord] = []
    for signal in long_signals:
        topic = hot_topic_by_id.get(signal.topic_id)
        if topic is None:
            continue
        support_count = len(signal.supporting_asset_ids) + len(signal.supporting_issue_ids)
        material_density = min(support_count / 4.0, 1.0)
        structure_readiness = min(max(support_count - 1, 0) / 3.0, 1.0)
        focus = 0.80 if len(topic.topic_label) >= 6 else 0.60
        writability_score = min(
            1.0,
            (0.35 * material_density)
            + (0.30 * structure_readiness)
            + (0.20 * signal.signal_score)
            + (0.15 * focus),
        )
        reasons = []
        if material_density >= 0.50:
            reasons.append("ENOUGH_ASSET_SUPPORT")
        if len(signal.supporting_issue_ids) > 0:
            reasons.append("ENOUGH_ISSUE_SUPPORT")
        if structure_readiness >= 0.50:
            reasons.append("CLEAR_STRUCTURE")
        if signal.signal_score >= 0.70:
            reasons.append("LONG_SIGNAL_CONFIRMED")
        if writability_score >= float(runtime_overrides.get("topic_selected_threshold", 0.68)):
            outcome = "SELECTED"
        elif writability_score >= float(runtime_overrides.get("topic_review_threshold", 0.48)):
            outcome = "REVIEW_REQUIRED"
        else:
            outcome = "OMITTED"
            reasons.append("TOPIC_TOO_THIN")
        bundle_outline_seed = ["背景与主题定义", "本周期关键事实", "可复用模式", "后续观察点"]
        review_flags = list(signal.review_flags)
        if outcome == "REVIEW_REQUIRED":
            review_flags.append("WRITABILITY_BORDERLINE")
        assessments.append(
            TopicWritabilityAssessment(
                topic_id=signal.topic_id,
                writability_score=round(writability_score, 4),
                writability_reasons=sorted(set(reasons)),
                recommended_outcome=outcome,
                supporting_asset_ids=list(signal.supporting_asset_ids),
                supporting_issue_ids=list(signal.supporting_issue_ids),
                bundle_outline_seed=bundle_outline_seed,
                review_flags=sorted(set(review_flags)),
                run_id=run_id,
            )
        )
    return assessments, failures


def assemble_topic_asset_bundle(
    period_asset_set: PeriodAssetSet,
    hot_topics: list[HotTopicSignal],
    topic_assessments: list[TopicWritabilityAssessment],
    run_id: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[list[LongCycleAsset], list[AuthorReviewItem], list[LongCycleFailureRecord]]:
    runtime_overrides = runtime_overrides or {}
    assets: list[LongCycleAsset] = []
    review_items: list[AuthorReviewItem] = []
    failures: list[LongCycleFailureRecord] = []
    hot_topic_by_id = {item.topic_id: item for item in hot_topics}
    for assessment in topic_assessments:
        topic = hot_topic_by_id.get(assessment.topic_id)
        if topic is None:
            continue
        if assessment.recommended_outcome == "SELECTED":
            if runtime_overrides.get("force_topic_bundle_failure"):
                failures.append(
                    _make_failure(
                        run_id=run_id,
                        step_name="assemble_topic_asset_bundle",
                        scope_type="TOPIC",
                        scope_id=assessment.topic_id,
                        failure_type="TOPIC_BUNDLE_ASSEMBLY_ERROR",
                        message="forced topic bundle failure",
                        details={"topic_id": assessment.topic_id},
                        retryable=False,
                    )
                )
                continue
            assets.append(
                LongCycleAsset(
                    long_cycle_asset_id=make_asset_id("TOPIC", assessment.topic_id, run_id),
                    asset_scope="TOPIC",
                    title=f"Topic Bundle: {topic.topic_label}",
                    summary=f"A reusable topic bundle for {topic.topic_label.lower()} built from retained knowledge and daily review signals.",
                    source_knowledge_asset_ids=list(period_asset_set.knowledge_asset_ids),
                    source_daily_review_issue_ids=list(period_asset_set.daily_review_issue_ids),
                    theme_ids=[assessment.topic_id],
                    asset_status="READY" if not assessment.review_flags else "NEEDS_AUTHOR_REVIEW",
                    generated_at=iso_now(),
                    run_id=run_id,
                    writability_score=assessment.writability_score,
                    structure={
                        "headline": f"Topic Bundle: {topic.topic_label}",
                        "summary": f"A reusable topic bundle for {topic.topic_label.lower()}.",
                        "angles": assessment.bundle_outline_seed[:2],
                        "sections": assessment.bundle_outline_seed,
                    },
                )
            )
        elif assessment.recommended_outcome == "REVIEW_REQUIRED":
            review_items.append(
                AuthorReviewItem(
                    review_item_id=make_review_item_id("TOPIC_DRAFT", assessment.topic_id),
                    review_scope="TOPIC_DRAFT",
                    related_object_id=assessment.topic_id,
                    review_flags=sorted(set(assessment.review_flags or ["WRITABILITY_BORDERLINE"])),
                    supporting_evidence={
                        "writability_score": assessment.writability_score,
                        "supporting_asset_ids": assessment.supporting_asset_ids,
                        "supporting_issue_ids": assessment.supporting_issue_ids,
                    },
                    suggested_action="WAIT_FOR_MORE_EVIDENCE",
                    run_id=run_id,
                )
            )
    return assets, review_items, failures


def run_pipeline(
    knowledge_assets_path: str,
    daily_review_issues_path: str,
    output_root: str,
    period_start: str | None = None,
    period_end: str | None = None,
    run_id: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    mode: str = "NORMAL",
) -> dict[str, Any]:
    del mode
    resolved_run_id = run_id or generate_run_id()
    runtime_overrides = runtime_overrides or {}
    try:
        knowledge_assets = load_json_array(knowledge_assets_path)
        daily_review_issues = load_json_array(daily_review_issues_path)
        run_dir = prepare_output_directory(output_root, resolved_run_id)
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": {}}

    workflow_started_at = iso_now()
    recorder = StepRecorder(run_id=resolved_run_id, started_at=workflow_started_at)
    all_failures: list[LongCycleFailureRecord] = []
    all_assets: list[LongCycleAsset] = []
    all_review_items: list[AuthorReviewItem] = []
    metrics: dict[str, Any] = {
        "knowledge_asset_input_count": len(knowledge_assets),
        "daily_review_issue_input_count": len(daily_review_issues),
        "hot_topic_count": 0,
        "long_signal_count": 0,
        "topic_assessment_count": 0,
        "weekly_asset_count": 0,
        "topic_asset_count": 0,
        "author_review_item_count": 0,
        "failure_record_count": 0,
        "workflow_duration_ms": 0,
    }
    artifact_paths = {
        "long_cycle_assets": str(run_dir / "long-cycle-assets.json"),
        "author_review": str(run_dir / "author-review.json"),
        "long_cycle_failures": str(run_dir / "long-cycle-failures.json"),
        "step_manifest": str(run_dir / "step-manifest.json"),
        "long_cycle_report": str(run_dir / "long-cycle-report.md"),
    }

    step_started = iso_now()
    period_asset_set, failures = collect_period_assets(knowledge_assets, daily_review_issues, resolved_run_id, period_start, period_end)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("collect_period_assets", determine_step_status(1), len(knowledge_assets) + len(daily_review_issues), 1, 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    hot_topics, failures = detect_hot_topics(period_asset_set, knowledge_assets, daily_review_issues, resolved_run_id, runtime_overrides)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["hot_topic_count"] = len(hot_topics)
    recorder.record("detect_hot_topics", determine_step_status(len(hot_topics)), 1, len(hot_topics), sum(1 for item in hot_topics if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    long_signals, failures = identify_long_signals(period_asset_set, hot_topics, knowledge_assets, daily_review_issues, resolved_run_id, runtime_overrides)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["long_signal_count"] = len(long_signals)
    recorder.record("identify_long_signals", determine_step_status(len(long_signals)), len(hot_topics), len(long_signals), sum(1 for item in long_signals if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    weekly_assets, review_items, failures = compose_weekly_assets(period_asset_set, hot_topics, long_signals, resolved_run_id, runtime_overrides)
    step_finished = iso_now()
    all_failures.extend(failures)
    all_assets.extend(weekly_assets)
    all_review_items.extend(review_items)
    metrics["weekly_asset_count"] = len(weekly_assets)
    recorder.record("compose_weekly_assets", determine_step_status(len(weekly_assets) + len(review_items)), len(long_signals), len(weekly_assets), len(review_items), len(failures), step_started, step_finished)

    step_started = iso_now()
    topic_assessments, failures = evaluate_topic_writability(period_asset_set, hot_topics, long_signals, resolved_run_id, runtime_overrides)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["topic_assessment_count"] = len(topic_assessments)
    recorder.record("evaluate_topic_writability", determine_step_status(len(topic_assessments)), len(long_signals), len(topic_assessments), sum(1 for item in topic_assessments if item.recommended_outcome == "REVIEW_REQUIRED"), len(failures), step_started, step_finished)

    step_started = iso_now()
    topic_assets, review_items, failures = assemble_topic_asset_bundle(period_asset_set, hot_topics, topic_assessments, resolved_run_id, runtime_overrides)
    step_finished = iso_now()
    all_failures.extend(failures)
    all_assets.extend(topic_assets)
    all_review_items.extend(review_items)
    metrics["topic_asset_count"] = len(topic_assets)
    metrics["author_review_item_count"] = len(all_review_items)
    metrics["failure_record_count"] = len(all_failures)
    recorder.record("assemble_topic_asset_bundle", determine_step_status(len(topic_assets) + len(review_items)), len(topic_assessments), len(topic_assets), len(review_items), len(failures), step_started, step_finished)

    workflow_finished_at = iso_now()
    metrics["workflow_duration_ms"] = _duration_ms(workflow_started_at, workflow_finished_at)
    metrics["failure_record_count"] = len(all_failures)
    manifest = recorder.build_manifest(workflow_finished_at, all_failures, artifact_paths)
    report = build_long_cycle_report(
        manifest,
        period_asset_set,
        hot_topics,
        long_signals,
        topic_assessments,
        all_assets,
        all_review_items,
        all_failures,
        metrics,
        workflow_finished_at,
    )

    try:
        write_json(artifact_paths["long_cycle_assets"], all_assets)
        write_json(artifact_paths["author_review"], all_review_items)
        write_json(artifact_paths["long_cycle_failures"], all_failures)
        write_json(artifact_paths["step_manifest"], manifest)
        write_text(artifact_paths["long_cycle_report"], render_long_cycle_report(report))
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": {}}

    return {
        "run_id": resolved_run_id,
        "workflow_status": manifest.workflow_status,
        "artifact_paths": artifact_paths,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the generate-long-cycle-assets workflow")
    parser.add_argument("--knowledge-assets-path", required=True)
    parser.add_argument("--daily-review-issues-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--period-start")
    parser.add_argument("--period-end")
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_pipeline(
        knowledge_assets_path=args.knowledge_assets_path,
        daily_review_issues_path=args.daily_review_issues_path,
        output_root=args.output_root,
        period_start=args.period_start,
        period_end=args.period_end,
        run_id=args.run_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["workflow_status"] != "FAILED" else 1


def _tokens_for_asset(asset: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    topic_tags = asset.get("topic_tags", []) or []
    for tag in topic_tags:
        normalized = slugify(str(tag))
        if normalized and len(normalized) >= 5 and normalized not in STOPWORDS:
            tokens.add(normalized)
    if not tokens:
        text = " ".join(part for part in [asset.get("title") or "", asset.get("summary") or ""] if part)
        tokens.update(_extract_tokens(text))
    return tokens


def _tokens_for_issue(issue: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    top_themes = issue.get("top_themes", []) or []
    for theme in top_themes:
        tokens.update(_extract_tokens(str(theme)))
    if not tokens:
        sections = issue.get("sections", {}) or {}
        for entries in sections.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                tokens.update(_extract_tokens(entry.get("headline") or ""))
                tokens.update(_extract_tokens(entry.get("summary") or ""))
    return tokens


def _extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in slugify(text).split("-"):
        if len(token) < 5 or token in STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def _signal_type_for_topic(topic: HotTopicSignal, asset_type_by_id: dict[str, str | None]) -> str:
    asset_types = {asset_type_by_id.get(item) for item in topic.supporting_knowledge_asset_ids}
    if "PLAYBOOK" in asset_types:
        return "PLAYBOOK"
    if "PATTERN" in asset_types:
        return "PATTERN"
    return "THEME"


def _topic_title(topic_id: str, hot_topics: list[HotTopicSignal]) -> str:
    for topic in hot_topics:
        if topic.topic_id == topic_id:
            return topic.topic_label
    return topic_id


def _resolve_period_start(knowledge_assets: list[dict[str, Any]], daily_review_issues: list[dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for asset in knowledge_assets:
        value = ensure_utc_iso(asset.get("stored_at"))
        if value:
            candidates.append(value)
    for issue in daily_review_issues:
        issue_date = issue.get("issue_date")
        if issue_date:
            candidates.append(ensure_utc_iso(f"{issue_date}T00:00:00+00:00") or "")
    filtered = [item for item in candidates if item]
    return min(filtered) if filtered else None


def _resolve_period_end(knowledge_assets: list[dict[str, Any]], daily_review_issues: list[dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for asset in knowledge_assets:
        value = ensure_utc_iso(asset.get("stored_at"))
        if value:
            candidates.append(value)
    for issue in daily_review_issues:
        issue_date = issue.get("issue_date")
        if issue_date:
            candidates.append(ensure_utc_iso(f"{issue_date}T23:59:59+00:00") or "")
    filtered = [item for item in candidates if item]
    return max(filtered) if filtered else None


def _make_failure(
    run_id: str,
    step_name: str,
    scope_type: str,
    scope_id: str | None,
    failure_type: str,
    message: str,
    details: dict[str, Any],
    retryable: bool,
) -> LongCycleFailureRecord:
    return LongCycleFailureRecord(
        failure_id=make_failure_id(run_id, step_name, scope_type, scope_id, message),
        run_id=run_id,
        step_name=step_name,
        scope_type=scope_type,
        scope_id=scope_id,
        failure_type=failure_type,
        message=message,
        details=details,
        retryable=retryable,
        recorded_at=iso_now(),
    )


def _duration_ms(started_at: str, finished_at: str) -> int:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    return int((end - start).total_seconds() * 1000)
