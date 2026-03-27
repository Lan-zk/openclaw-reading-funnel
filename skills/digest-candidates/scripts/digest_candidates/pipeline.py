"""Pipeline entrypoint for digest-candidates."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .io_utils import (
    ensure_utc_iso,
    generate_run_id,
    iso_now,
    load_normalized_candidates,
    load_preference_signals,
    make_cluster_id,
    make_digest_candidate_id,
    make_failure_id,
    make_review_item_id,
    make_url_fingerprint,
    normalize_url,
    parse_iso_datetime,
    prepare_output_directory,
    write_json,
    write_text,
)
from .models import (
    CandidateCluster,
    CanonicalCandidate,
    DigestCandidate,
    DigestEvidence,
    DigestFailureRecord,
    DigestReviewItem,
    ExactDedupResult,
    ExtractedContent,
    NormalizedCandidate,
)
from .reporting import (
    StepRecorder,
    build_digest_report,
    determine_step_status,
    render_digest_report,
)


def canonicalize_url(
    candidates: list[NormalizedCandidate],
    run_id: str,
) -> tuple[list[CanonicalCandidate], list[DigestFailureRecord]]:
    outputs: list[CanonicalCandidate] = []
    failures: list[DigestFailureRecord] = []
    for candidate in candidates:
        try:
            canonical_url = normalize_url(candidate.canonical_url)
            if canonical_url is None and not (candidate.normalized_title or candidate.title):
                raise ValueError("candidate requires url or title to continue")
            outputs.append(
                CanonicalCandidate(
                    normalized_candidate_id=candidate.normalized_candidate_id,
                    canonical_url=canonical_url,
                    url_fingerprint=make_url_fingerprint(canonical_url),
                    canonicalize_status="CANONICALIZED",
                    title=candidate.title,
                    normalized_title=candidate.normalized_title,
                    summary=candidate.summary,
                    published_at=ensure_utc_iso(candidate.published_at),
                    source_id=candidate.source_id,
                    source_name=candidate.source_name,
                    run_id=run_id,
                )
            )
        except Exception as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="canonicalize_url",
                    scope_type="CANDIDATE",
                    scope_id=candidate.normalized_candidate_id,
                    failure_type="CANONICALIZE_ERROR",
                    message=str(exc),
                    details={"normalized_candidate_id": candidate.normalized_candidate_id},
                    retryable=False,
                )
            )
    return outputs, failures


def exact_dedup(
    canonical_candidates: list[CanonicalCandidate],
    run_id: str,
) -> tuple[list[ExactDedupResult], list[DigestFailureRecord]]:
    grouped: dict[str, list[CanonicalCandidate]] = defaultdict(list)
    for candidate in canonical_candidates:
        dedup_key = candidate.url_fingerprint or candidate.canonical_url or candidate.normalized_candidate_id
        grouped[dedup_key].append(candidate)

    results: list[ExactDedupResult] = []
    for dedup_key, items in grouped.items():
        ordered = sorted(items, key=_survivor_sort_key, reverse=True)
        survivor = ordered[0]
        duplicates = [item.normalized_candidate_id for item in ordered[1:]]
        reason = "SAME_URL_FINGERPRINT" if survivor.url_fingerprint else "FALLBACK_CANONICAL_KEY"
        results.append(
            ExactDedupResult(
                survivor_candidate_id=survivor.normalized_candidate_id,
                duplicate_candidate_ids=duplicates,
                dedup_key=dedup_key,
                dedup_reason=reason,
                run_id=run_id,
            )
        )
    return results, []


def near_duplicate_cluster(
    dedup_results: list[ExactDedupResult],
    run_id: str,
) -> tuple[list[CandidateCluster], list[DigestFailureRecord]]:
    clusters: list[CandidateCluster] = []
    for result in dedup_results:
        member_ids = [result.survivor_candidate_id, *result.duplicate_candidate_ids]
        clusters.append(
            CandidateCluster(
                cluster_id=make_cluster_id(member_ids),
                member_candidate_ids=member_ids,
                primary_candidate_id=result.survivor_candidate_id,
                cluster_type="SINGLE" if len(member_ids) == 1 else "NEAR_DUPLICATE",
                cluster_confidence=0.95 if len(member_ids) == 1 else 1.0,
                cluster_signals=["EXACT_DUPLICATE_FOLD"] if len(member_ids) > 1 else ["SOLO_CANDIDATE"],
                run_id=run_id,
            )
        )
    return clusters, []


def extract_main_content(
    clusters: list[CandidateCluster],
    candidate_by_id: dict[str, CanonicalCandidate],
    run_id: str,
) -> tuple[list[ExtractedContent], list[DigestFailureRecord]]:
    outputs: list[ExtractedContent] = []
    failures: list[DigestFailureRecord] = []
    for cluster in clusters:
        candidate = candidate_by_id.get(cluster.primary_candidate_id)
        if candidate is None:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="extract_main_content",
                    scope_type="CLUSTER",
                    scope_id=cluster.cluster_id,
                    failure_type="EXTRACT_ERROR",
                    message="primary candidate missing for cluster",
                    details={"cluster_id": cluster.cluster_id},
                    retryable=False,
                )
            )
            continue
        parts = [item.strip() for item in [candidate.title or "", candidate.summary or ""] if item and item.strip()]
        raw_content = "\n\n".join(parts) if parts else None
        outputs.append(
            ExtractedContent(
                cluster_id=cluster.cluster_id,
                primary_candidate_id=cluster.primary_candidate_id,
                raw_content=raw_content,
                clean_content=raw_content,
                content_length=len(raw_content or ""),
                extract_status="EXTRACTED" if candidate.summary else ("RAW_ONLY" if candidate.title else "EXTRACTED_PARTIAL"),
                content_flags=[] if raw_content else ["NO_EXTRACTABLE_TEXT"],
                run_id=run_id,
            )
        )
    return outputs, failures


def clean_content(contents: list[ExtractedContent], run_id: str) -> tuple[list[ExtractedContent], list[DigestFailureRecord]]:
    outputs: list[ExtractedContent] = []
    for content in contents:
        clean_text = _normalize_whitespace(content.raw_content)
        flags = list(content.content_flags)
        if clean_text is None:
            flags = sorted(set(flags + ["EMPTY_AFTER_CLEAN"]))
        outputs.append(
            ExtractedContent(
                cluster_id=content.cluster_id,
                primary_candidate_id=content.primary_candidate_id,
                raw_content=content.raw_content,
                clean_content=clean_text,
                content_length=len(clean_text or ""),
                extract_status=content.extract_status,
                content_flags=flags,
                run_id=run_id,
            )
        )
    return outputs, []


def check_quality(
    contents: list[ExtractedContent],
    candidate_by_id: dict[str, CanonicalCandidate],
    run_id: str,
) -> tuple[list[DigestEvidence], list[DigestFailureRecord]]:
    evidence_list: list[DigestEvidence] = []
    for content in contents:
        candidate = candidate_by_id[content.primary_candidate_id]
        length = len(content.clean_content or "")
        completeness = 1.0 if candidate.summary else (0.45 if candidate.title else 0.0)
        readability = min(length / 30.0, 1.0)
        credibility = 0.8 if candidate.canonical_url else 0.4
        specificity = min(length / 60.0, 1.0)
        quality_score = round(
            (0.35 * completeness) + (0.25 * readability) + (0.20 * credibility) + (0.20 * specificity),
            4,
        )
        review_flags: list[str] = []
        if not candidate.summary:
            review_flags.append("SUMMARY_MISSING")
        if not candidate.published_at:
            review_flags.append("PUBLISHED_AT_MISSING")
        evidence_list.append(
            DigestEvidence(
                cluster_id=content.cluster_id,
                primary_candidate_id=content.primary_candidate_id,
                quality_score=quality_score,
                noise_flags=[],
                summary=None,
                summary_status="UNAVAILABLE",
                freshness_score=None,
                base_digest_score=None,
                rerank_score=None,
                review_flags=review_flags,
                supporting_signals={
                    "quality_components": {
                        "completeness": round(completeness, 4),
                        "readability": round(readability, 4),
                        "credibility": round(credibility, 4),
                        "specificity": round(specificity, 4),
                    }
                },
                run_id=run_id,
            )
        )
    return evidence_list, []


def filter_noise(
    evidence_list: list[DigestEvidence],
    contents: list[ExtractedContent],
    run_id: str,
) -> tuple[list[DigestEvidence], list[DigestFailureRecord]]:
    content_by_cluster = {item.cluster_id: item for item in contents}
    outputs: list[DigestEvidence] = []
    for evidence in evidence_list:
        content = content_by_cluster[evidence.cluster_id]
        noise_flags = list(evidence.noise_flags)
        if content.content_length == 0:
            noise_flags.append("EMPTY_SHELL")
        elif content.content_length < 8:
            noise_flags.append("LOW_INFO_DENSITY")
        outputs.append(
            DigestEvidence(
                cluster_id=evidence.cluster_id,
                primary_candidate_id=evidence.primary_candidate_id,
                quality_score=evidence.quality_score,
                noise_flags=sorted(set(noise_flags)),
                summary=evidence.summary,
                summary_status=evidence.summary_status,
                freshness_score=evidence.freshness_score,
                base_digest_score=evidence.base_digest_score,
                rerank_score=evidence.rerank_score,
                review_flags=list(evidence.review_flags),
                supporting_signals=dict(evidence.supporting_signals),
                run_id=run_id,
            )
        )
    return outputs, []


def generate_summary(
    evidence_list: list[DigestEvidence],
    contents: list[ExtractedContent],
    candidate_by_id: dict[str, CanonicalCandidate],
    run_id: str,
) -> tuple[list[DigestEvidence], list[DigestFailureRecord]]:
    content_by_cluster = {item.cluster_id: item for item in contents}
    outputs: list[DigestEvidence] = []
    for evidence in evidence_list:
        candidate = candidate_by_id[evidence.primary_candidate_id]
        content = content_by_cluster[evidence.cluster_id]
        summary = _build_summary(candidate.summary, content.clean_content)
        review_flags = list(evidence.review_flags)
        summary_status = "READY" if summary else "UNAVAILABLE"
        if not summary and content.content_length > 0:
            review_flags.append("SUMMARY_UNAVAILABLE")
        outputs.append(
            DigestEvidence(
                cluster_id=evidence.cluster_id,
                primary_candidate_id=evidence.primary_candidate_id,
                quality_score=evidence.quality_score,
                noise_flags=list(evidence.noise_flags),
                summary=summary,
                summary_status=summary_status,
                freshness_score=evidence.freshness_score,
                base_digest_score=evidence.base_digest_score,
                rerank_score=evidence.rerank_score,
                review_flags=sorted(set(review_flags)),
                supporting_signals=dict(evidence.supporting_signals),
                run_id=run_id,
            )
        )
    return outputs, []


def compute_digest_score(
    evidence_list: list[DigestEvidence],
    clusters: list[CandidateCluster],
    candidate_by_id: dict[str, CanonicalCandidate],
    preference_signals: list[dict[str, Any]] | None,
    run_id: str,
) -> tuple[list[DigestEvidence], list[DigestFailureRecord]]:
    cluster_by_id = {item.cluster_id: item for item in clusters}
    outputs: list[DigestEvidence] = []
    preferences = preference_signals or []
    for evidence in evidence_list:
        candidate = candidate_by_id[evidence.primary_candidate_id]
        cluster = cluster_by_id[evidence.cluster_id]
        info_density = min(
            (
                (evidence.supporting_signals.get("quality_components", {}).get("specificity") or 0.0)
                + (evidence.quality_score or 0.0)
            )
            / 2.0,
            1.0,
        )
        cluster_uniqueness = 1.0 if len(cluster.member_candidate_ids) == 1 else 0.8
        freshness_score = _compute_freshness_score(candidate.published_at)
        noise_penalty = 0.0
        if "LOW_INFO_DENSITY" in evidence.noise_flags:
            noise_penalty += 8.0
        if "EMPTY_SHELL" in evidence.noise_flags:
            noise_penalty += 25.0
        base_digest_score = round(
            100.0
            * (
                0.35 * (evidence.quality_score or 0.0)
                + 0.25 * freshness_score
                + 0.20 * info_density
                + 0.20 * cluster_uniqueness
            )
            - noise_penalty,
            2,
        )
        preference_adjustment = _compute_preference_adjustment(candidate, preferences)
        rerank_score = round(base_digest_score + preference_adjustment, 2)
        supporting_signals = dict(evidence.supporting_signals)
        supporting_signals["scoring"] = {
            "info_density": round(info_density, 4),
            "cluster_uniqueness": round(cluster_uniqueness, 4),
            "noise_penalty": round(noise_penalty, 2),
            "preference_adjustment": round(preference_adjustment, 2),
        }
        outputs.append(
            DigestEvidence(
                cluster_id=evidence.cluster_id,
                primary_candidate_id=evidence.primary_candidate_id,
                quality_score=evidence.quality_score,
                noise_flags=list(evidence.noise_flags),
                summary=evidence.summary,
                summary_status=evidence.summary_status,
                freshness_score=round(freshness_score, 4),
                base_digest_score=base_digest_score,
                rerank_score=rerank_score,
                review_flags=list(evidence.review_flags),
                supporting_signals=supporting_signals,
                run_id=run_id,
            )
        )
    return outputs, []


def assemble_digest_candidates(
    clusters: list[CandidateCluster],
    evidence_list: list[DigestEvidence],
    candidate_by_id: dict[str, CanonicalCandidate],
    run_id: str,
) -> tuple[list[DigestCandidate], list[DigestReviewItem], list[DigestFailureRecord]]:
    evidence_by_cluster = {item.cluster_id: item for item in evidence_list}
    digest_candidates: list[DigestCandidate] = []
    review_items: list[DigestReviewItem] = []
    failures: list[DigestFailureRecord] = []

    for cluster in sorted(clusters, key=lambda item: (evidence_by_cluster[item.cluster_id].rerank_score or 0.0), reverse=True):
        evidence = evidence_by_cluster.get(cluster.cluster_id)
        candidate = candidate_by_id.get(cluster.primary_candidate_id)
        if evidence is None or candidate is None:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="assemble_digest_candidates",
                    scope_type="CLUSTER",
                    scope_id=cluster.cluster_id,
                    failure_type="ASSEMBLY_ERROR",
                    message="cluster missing evidence or primary candidate",
                    details={"cluster_id": cluster.cluster_id},
                    retryable=False,
                )
            )
            continue

        digest_status = _decide_digest_status(evidence)
        digest_candidates.append(
            DigestCandidate(
                digest_candidate_id=make_digest_candidate_id(cluster.cluster_id),
                normalized_candidate_ids=list(cluster.member_candidate_ids),
                primary_normalized_candidate_id=cluster.primary_candidate_id,
                cluster_type=cluster.cluster_type,
                cluster_confidence=cluster.cluster_confidence,
                display_title=_display_title_for(candidate),
                display_summary=evidence.summary,
                canonical_url=candidate.canonical_url,
                quality_score=evidence.quality_score,
                freshness_score=evidence.freshness_score,
                digest_score=evidence.base_digest_score,
                noise_flags=list(evidence.noise_flags),
                needs_review=digest_status == "NEEDS_REVIEW",
                digest_status=digest_status,
                run_id=run_id,
            )
        )
        if digest_status == "NEEDS_REVIEW":
            review_items.append(
                DigestReviewItem(
                    review_item_id=make_review_item_id(cluster.cluster_id),
                    cluster_id=cluster.cluster_id,
                    primary_candidate_id=cluster.primary_candidate_id,
                    review_flags=list(evidence.review_flags),
                    supporting_evidence={
                        "summary": evidence.summary,
                        "quality_score": evidence.quality_score,
                        "freshness_score": evidence.freshness_score,
                        "base_digest_score": evidence.base_digest_score,
                        "noise_flags": list(evidence.noise_flags),
                    },
                    suggested_action=_suggested_action(evidence),
                    run_id=run_id,
                )
            )
    return digest_candidates, review_items, failures


def run_pipeline(
    normalized_candidates_path: str,
    output_root: str,
    run_id: str | None = None,
    preference_signals_path: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    mode: str = "NORMAL",
) -> dict[str, Any]:
    del runtime_overrides
    del mode
    resolved_run_id = run_id or generate_run_id()

    try:
        candidates = load_normalized_candidates(normalized_candidates_path)
    except Exception as exc:
        return {
            "run_id": resolved_run_id,
            "workflow_status": "FAILED",
            "error": str(exc),
            "artifact_paths": {},
        }

    try:
        preference_signals = load_preference_signals(preference_signals_path)
        run_dir = prepare_output_directory(output_root, resolved_run_id)
    except Exception as exc:
        return {
            "run_id": resolved_run_id,
            "workflow_status": "FAILED",
            "error": str(exc),
            "artifact_paths": {},
        }

    workflow_started_at = iso_now()
    recorder = StepRecorder(run_id=resolved_run_id, started_at=workflow_started_at)
    all_failures: list[DigestFailureRecord] = []
    metrics: dict[str, Any] = {
        "normalized_candidate_input_count": len(candidates),
        "canonical_candidate_count": 0,
        "exact_dedup_collapse_count": 0,
        "candidate_cluster_count": 0,
        "content_extract_success_count": 0,
        "content_extract_failure_count": 0,
        "summary_ready_count": 0,
        "review_item_count": 0,
        "kept_candidate_count": 0,
        "filtered_candidate_count": 0,
        "workflow_duration_ms": 0,
    }
    artifact_paths = {
        "digest_candidates": str(run_dir / "digest-candidates.json"),
        "digest_review": str(run_dir / "digest-review.json"),
        "digest_failures": str(run_dir / "digest-failures.json"),
        "step_manifest": str(run_dir / "step-manifest.json"),
        "digest_report": str(run_dir / "digest-report.md"),
    }

    step_started = iso_now()
    canonical_candidates, failures = canonicalize_url(candidates, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["canonical_candidate_count"] = len(canonical_candidates)
    recorder.record("canonicalize_url", determine_step_status(len(canonical_candidates)), len(candidates), len(canonical_candidates), 0, len(failures), step_started, step_finished)
    candidate_by_id = {item.normalized_candidate_id: item for item in canonical_candidates}

    step_started = iso_now()
    dedup_results, failures = exact_dedup(canonical_candidates, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["exact_dedup_collapse_count"] = sum(len(item.duplicate_candidate_ids) for item in dedup_results)
    recorder.record("exact_dedup", determine_step_status(len(dedup_results)), len(canonical_candidates), len(dedup_results), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    clusters, failures = near_duplicate_cluster(dedup_results, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["candidate_cluster_count"] = len(clusters)
    recorder.record("near_duplicate_cluster", determine_step_status(len(clusters)), len(dedup_results), len(clusters), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    contents, failures = extract_main_content(clusters, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["content_extract_success_count"] = len(contents)
    metrics["content_extract_failure_count"] = len(failures)
    recorder.record("extract_main_content", determine_step_status(len(contents)), len(clusters), len(contents), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    contents, failures = clean_content(contents, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("clean_content", determine_step_status(len(contents)), len(contents), len(contents), 0, len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = check_quality(contents, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("check_quality", determine_step_status(len(evidence_list)), len(contents), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = filter_noise(evidence_list, contents, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("filter_noise", determine_step_status(len(evidence_list)), len(evidence_list), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = generate_summary(evidence_list, contents, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["summary_ready_count"] = sum(1 for item in evidence_list if item.summary_status == "READY")
    recorder.record("generate_summary", determine_step_status(len(evidence_list)), len(evidence_list), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    evidence_list, failures = compute_digest_score(evidence_list, clusters, candidate_by_id, preference_signals, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record("compute_digest_score", determine_step_status(len(evidence_list)), len(evidence_list), len(evidence_list), sum(1 for item in evidence_list if item.review_flags), len(failures), step_started, step_finished)

    step_started = iso_now()
    digest_candidates, review_items, failures = assemble_digest_candidates(clusters, evidence_list, candidate_by_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["review_item_count"] = len(review_items)
    metrics["kept_candidate_count"] = sum(1 for item in digest_candidates if item.digest_status == "KEPT")
    metrics["filtered_candidate_count"] = sum(1 for item in digest_candidates if item.digest_status == "FILTERED")
    recorder.record("assemble_digest_candidates", determine_step_status(len(digest_candidates)), len(evidence_list), len(digest_candidates), len(review_items), len(failures), step_started, step_finished)

    workflow_finished_at = iso_now()
    started_at_dt = parse_iso_datetime(workflow_started_at) or datetime.now(timezone.utc)
    finished_at_dt = parse_iso_datetime(workflow_finished_at) or datetime.now(timezone.utc)
    metrics["workflow_duration_ms"] = max(0, int((finished_at_dt - started_at_dt).total_seconds() * 1000))
    manifest = recorder.build_manifest(workflow_finished_at, all_failures, artifact_paths)
    report = build_digest_report(manifest, digest_candidates, review_items, all_failures, metrics, workflow_finished_at)

    try:
        write_json(run_dir / "digest-candidates.json", digest_candidates)
        write_json(run_dir / "digest-review.json", review_items)
        write_json(run_dir / "digest-failures.json", all_failures)
        write_json(run_dir / "step-manifest.json", manifest)
        write_text(run_dir / "digest-report.md", render_digest_report(report))
    except Exception as exc:
        return {
            "run_id": resolved_run_id,
            "workflow_status": "FAILED",
            "error": str(exc),
            "artifact_paths": artifact_paths,
        }

    return {
        "run_id": resolved_run_id,
        "workflow_status": manifest.workflow_status,
        "artifact_paths": artifact_paths,
        "digest_candidate_count": len(digest_candidates),
        "review_item_count": len(review_items),
        "failure_record_count": len(all_failures),
    }


def _survivor_sort_key(candidate: CanonicalCandidate) -> tuple[int, int, int, str]:
    return (
        1 if candidate.canonical_url else 0,
        1 if candidate.summary else 0,
        1 if candidate.published_at else 0,
        candidate.normalized_candidate_id,
    )


def _normalize_whitespace(text: str | None) -> str | None:
    if text is None:
        return None
    value = " ".join(text.split())
    return value or None


def _build_summary(candidate_summary: str | None, clean_content: str | None) -> str | None:
    source = candidate_summary or clean_content
    if source is None:
        return None
    value = " ".join(source.split()).strip()
    if not value:
        return None
    return value[:180]


def _compute_freshness_score(published_at: str | None) -> float:
    published_dt = parse_iso_datetime(published_at)
    if published_dt is None:
        return 0.4
    age_hours = max(0.0, (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600.0)
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.8
    if age_hours <= 168:
        return 0.6
    return 0.35


def _compute_preference_adjustment(candidate: CanonicalCandidate, preference_signals: list[dict[str, Any]]) -> float:
    adjustment = 0.0
    for signal in preference_signals:
        if signal.get("signal_type") == "SOURCE_PREFERENCE" and signal.get("signal_value") == candidate.source_id:
            adjustment += float(signal.get("weight", 0.0))
    return max(-5.0, min(5.0, adjustment))


def _decide_digest_status(evidence: DigestEvidence) -> str:
    if evidence.review_flags:
        return "NEEDS_REVIEW"
    if "EMPTY_SHELL" in evidence.noise_flags:
        return "FILTERED"
    if (evidence.quality_score or 0.0) < 0.25:
        return "FILTERED"
    return "KEPT"


def _display_title_for(candidate: CanonicalCandidate) -> str:
    return candidate.title or candidate.normalized_title or candidate.canonical_url or candidate.normalized_candidate_id


def _suggested_action(evidence: DigestEvidence) -> str:
    if "SUMMARY_MISSING" in evidence.review_flags:
        return "RECHECK_EXTRACTION"
    if "PUBLISHED_AT_MISSING" in evidence.review_flags:
        return "KEEP_IF_VERIFIED"
    return "RECHECK_CLUSTER"


def _make_failure(
    run_id: str,
    step_name: str,
    scope_type: str,
    scope_id: str | None,
    failure_type: str,
    message: str,
    details: dict[str, Any],
    retryable: bool,
) -> DigestFailureRecord:
    return DigestFailureRecord(
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
    parser = argparse.ArgumentParser(description="Run the digest-candidates MVP pipeline.")
    parser.add_argument("--normalized-candidates-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--preference-signals-path")
    args = parser.parse_args(argv)
    result = run_pipeline(
        normalized_candidates_path=args.normalized_candidates_path,
        output_root=args.output_root,
        run_id=args.run_id,
        preference_signals_path=args.preference_signals_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["workflow_status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
