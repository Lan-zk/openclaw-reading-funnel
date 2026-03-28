"""Pipeline entrypoint for compose-daily-review."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .io_utils import (
    generate_run_id,
    iso_now,
    load_digest_candidates,
    load_preference_signals,
    make_entry_id,
    make_event_bundle_id,
    make_failure_id,
    make_issue_id,
    make_review_item_id,
    make_theme_id,
    normalize_url,
    parse_iso_datetime,
    prepare_output_directory,
    resolve_issue_date,
    slugify,
    write_json,
    write_text,
)
from .models import (
    DailyReviewDraft,
    DailyReviewEntry,
    DailyReviewEvidence,
    DailyReviewFailureRecord,
    DailyReviewIssue,
    DailyReviewTheme,
    DigestCandidate,
    EditorialReviewItem,
    EventBundle,
    ThemeSignal,
)
from .reporting import (
    StepRecorder,
    build_daily_review_report,
    determine_step_status,
    render_daily_review_report,
)


SECTION_ORDER = [
    "今日大事",
    "变更与实践",
    "安全与风险",
    "开源与工具",
    "洞察与数据点",
    "主题深挖",
]

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "after",
    "about",
    "today",
    "daily",
    "review",
    "update",
    "notes",
    "release",
}


def merge_same_event_candidates(
    digest_candidates: list[DigestCandidate],
    run_id: str,
) -> tuple[list[EventBundle], list[DailyReviewFailureRecord]]:
    grouped: dict[str, list[DigestCandidate]] = defaultdict(list)
    for candidate in digest_candidates:
        if candidate.digest_status == "FILTERED":
            continue
        group_key = normalize_url(candidate.canonical_url) or slugify(candidate.display_title)
        grouped[group_key].append(candidate)

    bundles: list[EventBundle] = []
    for group_key, items in grouped.items():
        ordered = sorted(items, key=_bundle_sort_key, reverse=True)
        primary = ordered[0]
        merge_confidence = 1.0 if len(items) > 1 and primary.canonical_url else (0.72 if len(items) > 1 else max(primary.cluster_confidence, 0.6))
        bundles.append(
            EventBundle(
                event_bundle_id=make_event_bundle_id(group_key),
                source_digest_candidate_ids=[item.digest_candidate_id for item in ordered],
                primary_digest_candidate_id=primary.digest_candidate_id,
                merge_confidence=round(min(1.0, merge_confidence), 4),
                event_scope="SINGLE_EVENT" if len(items) == 1 else "SAME_TOPIC_THREAD",
                bundle_title=primary.display_title,
                bundle_summary=primary.display_summary,
                supporting_signals={
                    "member_count": len(items),
                    "group_key": group_key,
                    "source_statuses": [item.digest_status for item in ordered],
                },
                run_id=run_id,
            )
        )
    return bundles, []


def classify_sections(
    bundles: list[EventBundle],
    candidate_by_id: dict[str, DigestCandidate],
    run_id: str,
) -> tuple[list[DailyReviewEvidence], list[DailyReviewFailureRecord]]:
    evidence_list: list[DailyReviewEvidence] = []
    failures: list[DailyReviewFailureRecord] = []
    for bundle in bundles:
        try:
            candidate = candidate_by_id[bundle.primary_digest_candidate_id]
            section, confidence, reasons = _classify_section(bundle, candidate)
            review_flags: list[str] = []
            if candidate.needs_review or candidate.digest_status == "NEEDS_REVIEW":
                review_flags.append("UPSTREAM_REVIEW_REQUIRED")
            if bundle.merge_confidence < 0.65:
                review_flags.append("MERGE_CONFIDENCE_LOW")
            if confidence < 0.7:
                review_flags.append("SECTION_CONFIDENCE_LOW")
            if not candidate.canonical_url:
                review_flags.append("CANONICAL_URL_MISSING")
            if not candidate.display_summary:
                review_flags.append("SUMMARY_MISSING")
            evidence_list.append(
                DailyReviewEvidence(
                    event_bundle_id=bundle.event_bundle_id,
                    proposed_section=section,
                    section_confidence=round(confidence, 4),
                    section_reasons=reasons,
                    daily_importance_score=None,
                    deep_dive_signal=False,
                    theme_ids=[],
                    review_flags=sorted(set(review_flags)),
                    supporting_signals={
                        "candidate_digest_status": candidate.digest_status,
                        "candidate_cluster_confidence": candidate.cluster_confidence,
                    },
                    run_id=run_id,
                )
            )
        except Exception as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="classify_sections",
                    scope_type="EVENT_BUNDLE",
                    scope_id=bundle.event_bundle_id,
                    failure_type="SECTION_CLASSIFY_ERROR",
                    message=str(exc),
                    details={"event_bundle_id": bundle.event_bundle_id},
                    retryable=False,
                )
            )
    return evidence_list, failures


def identify_top_themes(
    bundles: list[EventBundle],
    run_id: str,
) -> tuple[list[ThemeSignal], list[DailyReviewFailureRecord]]:
    keyword_groups: dict[str, list[EventBundle]] = defaultdict(list)
    for bundle in bundles:
        keyword = _primary_theme_keyword(bundle.bundle_title, bundle.bundle_summary)
        if keyword:
            keyword_groups[keyword].append(bundle)

    themes: list[ThemeSignal] = []
    for keyword, items in keyword_groups.items():
        if len(items) < 2:
            continue
        label = keyword.replace("-", " ").title()
        themes.append(
            ThemeSignal(
                theme_id=make_theme_id(label),
                supporting_event_bundle_ids=[item.event_bundle_id for item in items],
                theme_score=round(min(1.0, 0.45 + (0.15 * len(items))), 4),
                theme_type=_theme_type_for_keyword(keyword),
                theme_label=label,
                theme_summary=f"{label} appears across {len(items)} related event bundles today.",
                run_id=run_id,
            )
        )
    return themes, []


def score_daily_importance(
    evidence_list: list[DailyReviewEvidence],
    bundles: list[EventBundle],
    candidate_by_id: dict[str, DigestCandidate],
    preference_signals: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[DailyReviewEvidence], list[DailyReviewFailureRecord]]:
    bundle_by_id = {bundle.event_bundle_id: bundle for bundle in bundles}
    outputs: list[DailyReviewEvidence] = []
    failures: list[DailyReviewFailureRecord] = []
    for evidence in evidence_list:
        try:
            bundle = bundle_by_id[evidence.event_bundle_id]
            candidate = candidate_by_id[bundle.primary_digest_candidate_id]
            base_score = (
                0.45 * (candidate.digest_score or 0.0)
                + 0.25 * (candidate.quality_score or 0.0)
                + 0.15 * (candidate.freshness_score or 0.0)
                + 0.15 * bundle.merge_confidence
            )
            preference_adjustment = _preference_adjustment(candidate, preference_signals)
            if evidence.proposed_section == "今日大事":
                base_score += 0.07
            if evidence.proposed_section == "安全与风险":
                base_score += 0.05
            score = max(0.0, min(1.0, base_score + preference_adjustment))
            outputs.append(
                DailyReviewEvidence(
                    event_bundle_id=evidence.event_bundle_id,
                    proposed_section=evidence.proposed_section,
                    section_confidence=evidence.section_confidence,
                    section_reasons=list(evidence.section_reasons),
                    daily_importance_score=round(score, 4),
                    deep_dive_signal=evidence.deep_dive_signal,
                    theme_ids=list(evidence.theme_ids),
                    review_flags=list(evidence.review_flags),
                    supporting_signals={
                        **evidence.supporting_signals,
                        "importance_components": {
                            "digest_score": candidate.digest_score,
                            "quality_score": candidate.quality_score,
                            "freshness_score": candidate.freshness_score,
                            "merge_confidence": bundle.merge_confidence,
                            "preference_adjustment": round(preference_adjustment, 4),
                        },
                    },
                    run_id=evidence.run_id,
                )
            )
        except Exception as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="score_daily_importance",
                    scope_type="EVENT_BUNDLE",
                    scope_id=evidence.event_bundle_id,
                    failure_type="IMPORTANCE_SCORE_ERROR",
                    message=str(exc),
                    details={"event_bundle_id": evidence.event_bundle_id},
                    retryable=False,
                )
            )
    return outputs, failures


def detect_deep_dive_topics(
    evidence_list: list[DailyReviewEvidence],
    themes: list[ThemeSignal],
    bundles: list[EventBundle],
    candidate_by_id: dict[str, DigestCandidate],
    run_id: str,
) -> tuple[list[DailyReviewEvidence], list[DailyReviewFailureRecord]]:
    theme_ids_by_bundle: dict[str, list[str]] = defaultdict(list)
    for theme in themes:
        for event_bundle_id in theme.supporting_event_bundle_ids:
            theme_ids_by_bundle[event_bundle_id].append(theme.theme_id)

    bundle_by_id = {bundle.event_bundle_id: bundle for bundle in bundles}
    outputs: list[DailyReviewEvidence] = []
    failures: list[DailyReviewFailureRecord] = []
    for evidence in evidence_list:
        try:
            bundle = bundle_by_id[evidence.event_bundle_id]
            candidate = candidate_by_id[bundle.primary_digest_candidate_id]
            text = " ".join(part for part in [bundle.bundle_title or "", bundle.bundle_summary or ""] if part)
            deep_dive_signal = _looks_like_deep_dive(text, evidence.proposed_section, candidate)
            review_flags = list(evidence.review_flags)
            if deep_dive_signal and (evidence.daily_importance_score or 0.0) < 0.55:
                review_flags.append("DEEP_DIVE_CONFIDENCE_LOW")
            outputs.append(
                DailyReviewEvidence(
                    event_bundle_id=evidence.event_bundle_id,
                    proposed_section=evidence.proposed_section,
                    section_confidence=evidence.section_confidence,
                    section_reasons=list(evidence.section_reasons),
                    daily_importance_score=evidence.daily_importance_score,
                    deep_dive_signal=deep_dive_signal,
                    theme_ids=sorted(set(list(evidence.theme_ids) + theme_ids_by_bundle.get(evidence.event_bundle_id, []))),
                    review_flags=sorted(set(review_flags)),
                    supporting_signals=dict(evidence.supporting_signals),
                    run_id=evidence.run_id,
                )
            )
        except Exception as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="detect_deep_dive_topics",
                    scope_type="EVENT_BUNDLE",
                    scope_id=evidence.event_bundle_id,
                    failure_type="DEEP_DIVE_DETECT_ERROR",
                    message=str(exc),
                    details={"event_bundle_id": evidence.event_bundle_id},
                    retryable=False,
                )
            )
    return outputs, failures


def compose_issue_structure(
    bundles: list[EventBundle],
    themes: list[ThemeSignal],
    evidence_list: list[DailyReviewEvidence],
    candidate_by_id: dict[str, DigestCandidate],
    issue_date: str,
    run_id: str,
) -> tuple[DailyReviewDraft | None, list[EditorialReviewItem], list[DailyReviewFailureRecord]]:
    evidence_by_bundle = {item.event_bundle_id: item for item in evidence_list}
    sections = {section: [] for section in SECTION_ORDER}
    review_items: list[EditorialReviewItem] = []
    selected_bundle_ids: list[str] = []
    failures: list[DailyReviewFailureRecord] = []

    ordered_bundles = sorted(
        bundles,
        key=lambda item: _draft_sort_key(evidence_by_bundle.get(item.event_bundle_id), candidate_by_id[item.primary_digest_candidate_id]),
        reverse=True,
    )

    for bundle in ordered_bundles:
        evidence = evidence_by_bundle.get(bundle.event_bundle_id)
        if evidence is None:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="compose_issue_structure",
                    scope_type="EVENT_BUNDLE",
                    scope_id=bundle.event_bundle_id,
                    failure_type="MISSING_EVIDENCE",
                    message="missing evidence for event bundle",
                    details={"event_bundle_id": bundle.event_bundle_id},
                    retryable=False,
                )
            )
            continue
        candidate = candidate_by_id[bundle.primary_digest_candidate_id]
        decision = _decide_bundle_outcome(bundle, evidence, candidate)
        if decision == "SELECTED":
            section = "主题深挖" if evidence.deep_dive_signal and (evidence.daily_importance_score or 0.0) >= 0.7 else (evidence.proposed_section or "今日大事")
            sections[section].append(
                DailyReviewEntry(
                    entry_id=make_entry_id(bundle.event_bundle_id, section),
                    event_bundle_id=bundle.event_bundle_id,
                    section=section,
                    headline=bundle.bundle_title or candidate.display_title,
                    summary=bundle.bundle_summary or candidate.display_summary,
                    why_it_matters=_why_it_matters(section, evidence),
                    importance_score=evidence.daily_importance_score,
                    source_digest_candidate_ids=list(bundle.source_digest_candidate_ids),
                    theme_ids=list(evidence.theme_ids),
                    review_flags=[],
                )
            )
            selected_bundle_ids.append(bundle.event_bundle_id)
        elif decision == "REVIEW_REQUIRED":
            review_items.append(
                EditorialReviewItem(
                    review_item_id=make_review_item_id(bundle.event_bundle_id),
                    event_bundle_id=bundle.event_bundle_id,
                    review_flags=list(evidence.review_flags) or ["EDITORIAL_REVIEW_REQUIRED"],
                    supporting_evidence={
                        "proposed_section": evidence.proposed_section,
                        "section_confidence": evidence.section_confidence,
                        "daily_importance_score": evidence.daily_importance_score,
                        "theme_ids": list(evidence.theme_ids),
                        "deep_dive_signal": evidence.deep_dive_signal,
                        "source_digest_candidate_ids": list(bundle.source_digest_candidate_ids),
                    },
                    suggested_action=_suggested_action(evidence),
                    run_id=run_id,
                )
            )

    if not selected_bundle_ids and not review_items:
        return None, [], failures

    draft = DailyReviewDraft(
        issue_date=issue_date,
        section_entries=sections,
        top_themes=_select_issue_themes(themes, selected_bundle_ids),
        editorial_notes=_editorial_notes(sections, review_items),
        selected_event_bundle_ids=selected_bundle_ids,
        review_item_ids=[item.review_item_id for item in review_items],
        issue_status="NEEDS_EDITOR_REVIEW" if review_items else "COMPOSED",
        run_id=run_id,
    )
    return draft, review_items, failures


def render_human_readable_issue(
    draft: DailyReviewDraft | None,
    bundles: list[EventBundle],
    review_items: list[EditorialReviewItem],
    run_id: str,
) -> tuple[DailyReviewIssue | None, str, list[DailyReviewFailureRecord]]:
    if draft is None:
        return None, "# Daily Review\n\nNo formal issue composed for this run.\n", []

    bundle_by_id = {bundle.event_bundle_id: bundle for bundle in bundles}
    source_digest_candidate_ids: list[str] = []
    for bundle_id in draft.selected_event_bundle_ids:
        bundle = bundle_by_id.get(bundle_id)
        if bundle is not None:
            source_digest_candidate_ids.extend(bundle.source_digest_candidate_ids)

    issue = DailyReviewIssue(
        daily_review_issue_id=make_issue_id(draft.issue_date, run_id),
        issue_date=draft.issue_date,
        sections=draft.section_entries,
        top_themes=draft.top_themes,
        editorial_notes=draft.editorial_notes,
        source_digest_candidate_ids=sorted(set(source_digest_candidate_ids)),
        render_status=draft.issue_status,
        run_id=run_id,
    )
    markdown = _render_issue_markdown(issue, review_items)
    return issue, markdown, []


def run_pipeline(
    digest_candidates_path: str,
    output_root: str,
    issue_date: str | None = None,
    run_id: str | None = None,
    preference_signals_path: str | None = None,
    render_template_path: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    mode: str = "NORMAL",
) -> dict[str, Any]:
    del render_template_path
    del runtime_overrides
    resolved_run_id = run_id or generate_run_id()

    try:
        resolved_issue_date = resolve_issue_date(issue_date if mode == "REPLAY" or issue_date is not None else None)
        if mode == "REPLAY" and issue_date is None:
            raise ValueError("issue_date is required in REPLAY mode")
        digest_candidates = load_digest_candidates(digest_candidates_path)
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": {}}

    try:
        preference_signals = load_preference_signals(preference_signals_path)
        run_dir = prepare_output_directory(output_root, resolved_run_id)
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": {}}

    workflow_started_at = iso_now()
    recorder = StepRecorder(run_id=resolved_run_id, started_at=workflow_started_at)
    all_failures: list[DailyReviewFailureRecord] = []
    metrics: dict[str, Any] = {
        "digest_candidate_input_count": len(digest_candidates),
        "event_bundle_count": 0,
        "theme_signal_count": 0,
        "selected_event_bundle_count": 0,
        "omitted_event_bundle_count": 0,
        "review_required_bundle_count": 0,
        "editorial_review_item_count": 0,
        "issue_count": 0,
        "section_entry_count": 0,
        "deep_dive_entry_count": 0,
        "workflow_duration_ms": 0,
    }
    artifact_paths = {
        "daily_review_issues": str(run_dir / "daily-review-issues.json"),
        "editorial_review": str(run_dir / "editorial-review.json"),
        "daily_review_failures": str(run_dir / "daily-review-failures.json"),
        "step_manifest": str(run_dir / "step-manifest.json"),
        "daily_review_report": str(run_dir / "daily-review-report.md"),
        "daily_review_markdown": str(run_dir / "daily-review.md"),
    }

    candidate_by_id = {item.digest_candidate_id: item for item in digest_candidates if item.digest_status != "FILTERED"}

    step_started = iso_now()
    bundles, failures = merge_same_event_candidates(digest_candidates, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["event_bundle_count"] = len(bundles)
    recorder.record("merge_same_event_candidates", determine_step_status(len(bundles)), len(digest_candidates), len(bundles), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = classify_sections(bundles, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("classify_sections", determine_step_status(len(evidence_list)), len(bundles), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    themes, failures = identify_top_themes(bundles, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["theme_signal_count"] = len(themes)
    recorder.record("identify_top_themes", determine_step_status(len(themes)), len(bundles), len(themes), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = score_daily_importance(evidence_list, bundles, candidate_by_id, preference_signals, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("score_daily_importance", determine_step_status(len(evidence_list)), len(evidence_list), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = detect_deep_dive_topics(evidence_list, themes, bundles, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("detect_deep_dive_topics", determine_step_status(len(evidence_list)), len(evidence_list), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    draft, review_items, failures = compose_issue_structure(bundles, themes, evidence_list, candidate_by_id, resolved_issue_date, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    selected_bundle_ids = draft.selected_event_bundle_ids if draft else []
    metrics["selected_event_bundle_count"] = len(selected_bundle_ids)
    metrics["review_required_bundle_count"] = len(review_items)
    metrics["editorial_review_item_count"] = len(review_items)
    metrics["omitted_event_bundle_count"] = max(0, len(bundles) - len(selected_bundle_ids) - len(review_items))
    recorder.record("compose_issue_structure", determine_step_status(1 if draft is not None else 0), len(evidence_list), 1 if draft is not None else 0, len(review_items), len(failures), step_started, step_finished)

    step_started = iso_now()
    issue, daily_review_markdown, failures = render_human_readable_issue(draft, bundles, review_items, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    issues = [issue] if issue is not None else []
    metrics["issue_count"] = len(issues)
    metrics["section_entry_count"] = sum(len(entries) for entries in issue.sections.values()) if issue else 0
    metrics["deep_dive_entry_count"] = len(issue.sections.get("主题深挖", [])) if issue else 0
    recorder.record("render_human_readable_issue", determine_step_status(len(issues)), 1 if draft is not None else 0, len(issues), len(review_items), len(failures), step_started, step_finished)

    workflow_finished_at = iso_now()
    started_at_dt = parse_iso_datetime(workflow_started_at) or datetime.now(timezone.utc)
    finished_at_dt = parse_iso_datetime(workflow_finished_at) or datetime.now(timezone.utc)
    metrics["workflow_duration_ms"] = max(0, int((finished_at_dt - started_at_dt).total_seconds() * 1000))
    manifest = recorder.build_manifest(workflow_finished_at, all_failures, artifact_paths)
    report = build_daily_review_report(manifest, issues, review_items, all_failures, metrics, workflow_finished_at)

    try:
        write_json(run_dir / "daily-review-issues.json", issues)
        write_json(run_dir / "editorial-review.json", review_items)
        write_json(run_dir / "daily-review-failures.json", all_failures)
        write_json(run_dir / "step-manifest.json", manifest)
        write_text(run_dir / "daily-review-report.md", render_daily_review_report(report))
        write_text(run_dir / "daily-review.md", daily_review_markdown)
    except Exception as exc:
        return {"run_id": resolved_run_id, "workflow_status": "FAILED", "error": str(exc), "artifact_paths": artifact_paths}

    return {
        "run_id": resolved_run_id,
        "workflow_status": manifest.workflow_status,
        "artifact_paths": artifact_paths,
        "issue_count": len(issues),
        "review_item_count": len(review_items),
        "failure_record_count": len(all_failures),
    }


def _bundle_sort_key(candidate: DigestCandidate) -> tuple[float, float, float, str]:
    return (
        candidate.digest_score or 0.0,
        candidate.quality_score or 0.0,
        candidate.cluster_confidence,
        candidate.digest_candidate_id,
    )


def _draft_sort_key(evidence: DailyReviewEvidence | None, candidate: DigestCandidate) -> tuple[float, float, str]:
    return (
        evidence.daily_importance_score if evidence and evidence.daily_importance_score is not None else 0.0,
        candidate.digest_score or 0.0,
        candidate.digest_candidate_id,
    )


def _classify_section(bundle: EventBundle, candidate: DigestCandidate) -> tuple[str, float, list[str]]:
    text = " ".join(part for part in [bundle.bundle_title or "", bundle.bundle_summary or "", candidate.display_title, candidate.display_summary or ""] if part).lower()
    rules = [
        ("安全与风险", 0.92, ["Matches security or risk keywords"], ("security", "risk", "cve", "vulnerability", "incident", "patch")),
        ("开源与工具", 0.88, ["Matches open-source or tooling keywords"], ("open source", "tool", "cli", "sdk", "library", "framework")),
        ("洞察与数据点", 0.87, ["Matches data or insight keywords"], ("report", "survey", "benchmark", "data", "metrics", "analysis")),
        ("变更与实践", 0.84, ["Matches change or practice keywords"], ("release", "migration", "how to", "guide", "practice", "deploy")),
    ]
    for section, confidence, reasons, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return section, confidence, reasons
    return "今日大事", 0.68, ["Fallback to major daily item when no stronger section match exists"]


def _primary_theme_keyword(title: str | None, summary: str | None) -> str | None:
    text = " ".join(part for part in [title or "", summary or ""] if part).lower()
    tokens = [token.strip("-") for token in slugify(text).split("-") if token.strip("-")]
    for token in tokens:
        if len(token) >= 4 and token not in STOPWORDS:
            return token
    return None


def _theme_type_for_keyword(keyword: str) -> str:
    if keyword in {"security", "risk", "cve"}:
        return "RISK"
    if keyword in {"tooling", "python", "sdk", "cli", "framework"}:
        return "TOOLING"
    if keyword in {"benchmark", "survey", "report", "analysis"}:
        return "INSIGHT"
    return "PRACTICE"


def _preference_adjustment(candidate: DigestCandidate, preference_signals: list[dict[str, Any]]) -> float:
    adjustment = 0.0
    title = candidate.display_title.lower()
    url = (candidate.canonical_url or "").lower()
    for signal in preference_signals:
        signal_type = signal.get("signal_type")
        signal_value = str(signal.get("signal_value", "")).lower()
        if signal_type == "TOPIC_PREFERENCE" and signal_value and signal_value in title:
            adjustment += float(signal.get("weight", 0.0)) * 0.02
        if signal_type == "URL_PREFERENCE" and signal_value and signal_value in url:
            adjustment += float(signal.get("weight", 0.0)) * 0.01
    return max(-0.05, min(0.05, adjustment))


def _looks_like_deep_dive(text: str, proposed_section: str | None, candidate: DigestCandidate) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("analysis", "report", "survey", "guide", "architecture", "deep dive")):
        return True
    if proposed_section == "洞察与数据点" and (candidate.quality_score or 0.0) >= 0.75:
        return True
    return False


def _decide_bundle_outcome(bundle: EventBundle, evidence: DailyReviewEvidence, candidate: DigestCandidate) -> str:
    if candidate.digest_status == "FILTERED":
        return "OMITTED"
    if evidence.review_flags:
        return "REVIEW_REQUIRED"
    if (evidence.daily_importance_score or 0.0) < 0.5:
        return "OMITTED"
    if bundle.merge_confidence < 0.55:
        return "REVIEW_REQUIRED"
    return "SELECTED"


def _select_issue_themes(themes: list[ThemeSignal], selected_bundle_ids: list[str]) -> list[DailyReviewTheme]:
    selected = []
    selected_set = set(selected_bundle_ids)
    for theme in sorted(themes, key=lambda item: item.theme_score, reverse=True):
        if selected_set and not selected_set.intersection(theme.supporting_event_bundle_ids):
            continue
        selected.append(
            DailyReviewTheme(
                theme_id=theme.theme_id,
                theme_label=theme.theme_label,
                theme_summary=theme.theme_summary,
                supporting_event_bundle_ids=list(theme.supporting_event_bundle_ids),
                theme_score=theme.theme_score,
            )
        )
        if len(selected) >= 3:
            break
    return selected


def _why_it_matters(section: str, evidence: DailyReviewEvidence) -> str:
    score = evidence.daily_importance_score or 0.0
    if section == "安全与风险":
        return f"Risk-oriented item with daily importance {score:.2f}."
    if section == "主题深挖":
        return f"Strong deep-dive candidate with daily importance {score:.2f}."
    return f"Selected for the {section} section with daily importance {score:.2f}."


def _suggested_action(evidence: DailyReviewEvidence) -> str:
    flags = set(evidence.review_flags)
    if "MERGE_CONFIDENCE_LOW" in flags:
        return "VERIFY_BUNDLE"
    if "SECTION_CONFIDENCE_LOW" in flags:
        return "VERIFY_SECTION"
    if "DEEP_DIVE_CONFIDENCE_LOW" in flags:
        return "VERIFY_DEEP_DIVE"
    return "VERIFY_PRIORITY"


def _editorial_notes(sections: dict[str, list[DailyReviewEntry]], review_items: list[EditorialReviewItem]) -> list[str]:
    notes: list[str] = []
    if review_items:
        notes.append(f"{len(review_items)} event bundles require editor review before final publication.")
    if not any(sections.values()):
        notes.append("No formally selected entries today; issue is review-driven.")
    if len(sections["主题深挖"]) > 1:
        notes.append("Theme deep-dive section may need manual compression.")
    return notes


def _render_issue_markdown(issue: DailyReviewIssue, review_items: list[EditorialReviewItem]) -> str:
    lines = [
        f"# Daily Review - {issue.issue_date}",
        "",
        f"- status: `{issue.render_status}`",
        f"- source_digest_candidate_count: {len(issue.source_digest_candidate_ids)}",
        "",
    ]
    if issue.top_themes:
        lines.extend(["## Top Themes", ""])
        for theme in issue.top_themes:
            summary = f": {theme.theme_summary}" if theme.theme_summary else ""
            lines.append(f"- {theme.theme_label} ({theme.theme_score:.2f}){summary}")
        lines.append("")
    for section in SECTION_ORDER:
        lines.extend([f"## {section}", ""])
        entries = issue.sections.get(section, [])
        if not entries:
            lines.append("- No entries")
            lines.append("")
            continue
        for entry in entries:
            lines.append(f"- {entry.headline}")
            if entry.summary:
                lines.append(f"  {entry.summary}")
            if entry.why_it_matters:
                lines.append(f"  Why it matters: {entry.why_it_matters}")
        lines.append("")
    if issue.editorial_notes:
        lines.extend(["## Editorial Notes", ""])
        for note in issue.editorial_notes:
            lines.append(f"- {note}")
        lines.append("")
    if review_items:
        lines.extend(["## Editorial Review Queue", ""])
        for item in review_items:
            lines.append(f"- {item.event_bundle_id}: {', '.join(item.review_flags)}")
    return "\n".join(lines).rstrip() + "\n"


def _make_failure(
    run_id: str,
    step_name: str,
    scope_type: str,
    scope_id: str | None,
    failure_type: str,
    message: str,
    details: dict[str, Any],
    retryable: bool,
) -> DailyReviewFailureRecord:
    return DailyReviewFailureRecord(
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the compose-daily-review MVP pipeline.")
    parser.add_argument("--digest-candidates-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--issue-date")
    parser.add_argument("--run-id")
    parser.add_argument("--preference-signals-path")
    parser.add_argument("--mode", default="NORMAL")
    args = parser.parse_args(argv)
    result = run_pipeline(
        digest_candidates_path=args.digest_candidates_path,
        output_root=args.output_root,
        issue_date=args.issue_date,
        run_id=args.run_id,
        preference_signals_path=args.preference_signals_path,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["workflow_status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
