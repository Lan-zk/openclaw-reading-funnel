"""Object models for compose-daily-review."""

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
class EventBundle(JsonModel):
    event_bundle_id: str
    source_digest_candidate_ids: list[str]
    primary_digest_candidate_id: str
    merge_confidence: float
    event_scope: str
    bundle_title: str | None
    bundle_summary: str | None
    supporting_signals: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""


@dataclass(slots=True)
class ThemeSignal(JsonModel):
    theme_id: str
    supporting_event_bundle_ids: list[str]
    theme_score: float
    theme_type: str
    theme_label: str
    theme_summary: str | None
    run_id: str


@dataclass(slots=True)
class DailyReviewEvidence(JsonModel):
    event_bundle_id: str
    proposed_section: str | None
    section_confidence: float | None
    section_reasons: list[str]
    daily_importance_score: float | None
    deep_dive_signal: bool
    theme_ids: list[str]
    review_flags: list[str]
    supporting_signals: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""


@dataclass(slots=True)
class DailyReviewEntry(JsonModel):
    entry_id: str
    event_bundle_id: str
    section: str
    headline: str
    summary: str | None
    why_it_matters: str | None
    importance_score: float | None
    source_digest_candidate_ids: list[str]
    theme_ids: list[str]
    review_flags: list[str]


@dataclass(slots=True)
class DailyReviewTheme(JsonModel):
    theme_id: str
    theme_label: str
    theme_summary: str | None
    supporting_event_bundle_ids: list[str]
    theme_score: float


@dataclass(slots=True)
class EditorialReviewItem(JsonModel):
    review_item_id: str
    event_bundle_id: str
    review_flags: list[str]
    supporting_evidence: dict[str, Any]
    suggested_action: str
    run_id: str


@dataclass(slots=True)
class DailyReviewDraft(JsonModel):
    issue_date: str
    section_entries: dict[str, list[DailyReviewEntry]]
    top_themes: list[DailyReviewTheme]
    editorial_notes: list[str]
    selected_event_bundle_ids: list[str]
    review_item_ids: list[str]
    issue_status: str
    run_id: str


@dataclass(slots=True)
class DailyReviewIssue(JsonModel):
    daily_review_issue_id: str
    issue_date: str
    sections: dict[str, list[DailyReviewEntry]]
    top_themes: list[DailyReviewTheme]
    editorial_notes: list[str]
    source_digest_candidate_ids: list[str]
    render_status: str
    run_id: str


@dataclass(slots=True)
class DailyReviewFailureRecord(JsonModel):
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
class DailyReviewStepResult(JsonModel):
    step_name: str
    status: str
    input_count: int
    output_count: int
    review_count: int
    failure_count: int
    started_at: str
    finished_at: str


@dataclass(slots=True)
class DailyReviewStepManifest(JsonModel):
    run_id: str
    workflow_name: str
    step_results: list[DailyReviewStepResult]
    started_at: str
    finished_at: str
    workflow_status: str
    artifact_paths: dict[str, str]


@dataclass(slots=True)
class DailyReviewReport(JsonModel):
    run_id: str
    workflow_status: str
    issue_summary: dict[str, Any]
    review_summary: dict[str, Any]
    failure_summary: dict[str, Any]
    artifact_summary: dict[str, Any]
    generated_at: str
