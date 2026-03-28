"""Object models for digest-candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


def _convert(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _convert(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_convert(item) for item in value]
    if isinstance(value, dict):
        return {key: _convert(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class JsonModel:
    def to_dict(self) -> dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class NormalizedCandidate(JsonModel):
    normalized_candidate_id: str
    source_entry_id: str
    canonical_url: str | None
    url_fingerprint: str | None
    title: str | None
    normalized_title: str | None
    summary: str | None
    language: str | None
    published_at: str | None
    source_id: str
    source_name: str
    normalize_status: str
    run_id: str


@dataclass(slots=True)
class CanonicalCandidate(JsonModel):
    normalized_candidate_id: str
    canonical_url: str | None
    url_fingerprint: str | None
    canonicalize_status: str
    title: str | None
    normalized_title: str | None
    summary: str | None
    published_at: str | None
    source_id: str
    source_name: str
    run_id: str


@dataclass(slots=True)
class ExactDedupResult(JsonModel):
    survivor_candidate_id: str
    duplicate_candidate_ids: list[str]
    dedup_key: str
    dedup_reason: str
    run_id: str


@dataclass(slots=True)
class CandidateCluster(JsonModel):
    cluster_id: str
    member_candidate_ids: list[str]
    primary_candidate_id: str
    cluster_type: str
    cluster_confidence: float
    cluster_signals: list[str] = field(default_factory=list)
    run_id: str = ""


@dataclass(slots=True)
class ExtractedContent(JsonModel):
    cluster_id: str
    primary_candidate_id: str
    raw_content: str | None
    clean_content: str | None
    content_length: int
    extract_status: str
    content_flags: list[str] = field(default_factory=list)
    run_id: str = ""


@dataclass(slots=True)
class DigestEvidence(JsonModel):
    cluster_id: str
    primary_candidate_id: str
    quality_score: float | None
    noise_flags: list[str]
    summary: str | None
    summary_status: str
    freshness_score: float | None
    base_digest_score: float | None
    rerank_score: float | None
    review_flags: list[str]
    supporting_signals: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""


@dataclass(slots=True)
class DigestCandidate(JsonModel):
    digest_candidate_id: str
    normalized_candidate_ids: list[str]
    primary_normalized_candidate_id: str
    cluster_type: str
    cluster_confidence: float
    display_title: str
    display_summary: str | None
    canonical_url: str | None
    quality_score: float | None
    freshness_score: float | None
    digest_score: float | None
    noise_flags: list[str]
    needs_review: bool
    digest_status: str
    run_id: str


@dataclass(slots=True)
class DigestReviewItem(JsonModel):
    review_item_id: str
    cluster_id: str
    primary_candidate_id: str
    review_flags: list[str]
    supporting_evidence: dict[str, Any]
    suggested_action: str
    run_id: str


@dataclass(slots=True)
class DigestFailureRecord(JsonModel):
    failure_id: str
    run_id: str
    step_name: str
    scope_type: str
    scope_id: str | None
    failure_type: str
    message: str
    details: dict[str, Any]
    retryable: bool
    recorded_at: str


@dataclass(slots=True)
class DigestStepResult(JsonModel):
    step_name: str
    status: str
    input_count: int
    output_count: int
    review_count: int
    failure_count: int
    started_at: str
    finished_at: str


@dataclass(slots=True)
class DigestStepManifest(JsonModel):
    run_id: str
    workflow_name: str
    step_results: list[DigestStepResult]
    started_at: str
    finished_at: str
    workflow_status: str
    artifact_paths: dict[str, str]


@dataclass(slots=True)
class DigestReport(JsonModel):
    run_id: str
    workflow_status: str
    candidate_summary: dict[str, Any]
    review_summary: dict[str, Any]
    failure_summary: dict[str, Any]
    artifact_summary: dict[str, Any]
    generated_at: str
