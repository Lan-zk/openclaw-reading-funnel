"""Object models for generate-long-cycle-assets."""

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
class PeriodAssetSet(JsonModel):
    period_id: str
    knowledge_asset_ids: list[str]
    daily_review_issue_ids: list[str]
    period_start: str
    period_end: str
    run_id: str


@dataclass(slots=True)
class HotTopicSignal(JsonModel):
    topic_id: str
    supporting_knowledge_asset_ids: list[str]
    supporting_issue_ids: list[str]
    heat_score: float
    topic_confidence: float
    topic_label: str
    topic_keywords: list[str]
    review_flags: list[str]
    run_id: str


@dataclass(slots=True)
class LongSignal(JsonModel):
    signal_id: str
    topic_id: str
    signal_type: str
    signal_score: float
    supporting_asset_ids: list[str]
    supporting_issue_ids: list[str]
    signal_summary: str | None
    review_flags: list[str]
    run_id: str


@dataclass(slots=True)
class TopicWritabilityAssessment(JsonModel):
    topic_id: str
    writability_score: float
    writability_reasons: list[str]
    recommended_outcome: str
    supporting_asset_ids: list[str]
    supporting_issue_ids: list[str]
    bundle_outline_seed: list[str]
    review_flags: list[str]
    run_id: str


@dataclass(slots=True)
class AuthorReviewItem(JsonModel):
    review_item_id: str
    review_scope: str
    related_object_id: str
    review_flags: list[str]
    supporting_evidence: dict[str, Any]
    suggested_action: str
    run_id: str


@dataclass(slots=True)
class LongCycleAsset(JsonModel):
    long_cycle_asset_id: str
    asset_scope: str
    title: str
    summary: str | None
    source_knowledge_asset_ids: list[str]
    source_daily_review_issue_ids: list[str]
    theme_ids: list[str]
    asset_status: str
    generated_at: str
    run_id: str
    writability_score: float | None
    structure: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LongCycleFailureRecord(JsonModel):
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
class LongCycleStepResult(JsonModel):
    step_name: str
    status: str
    input_count: int
    output_count: int
    review_count: int
    failure_count: int
    started_at: str
    finished_at: str


@dataclass(slots=True)
class LongCycleStepManifest(JsonModel):
    run_id: str
    workflow_name: str
    step_results: list[LongCycleStepResult]
    started_at: str
    finished_at: str
    workflow_status: str
    artifact_paths: dict[str, str]


@dataclass(slots=True)
class LongCycleReport(JsonModel):
    run_id: str
    workflow_status: str
    period_summary: dict[str, Any]
    signal_summary: dict[str, Any]
    asset_summary: dict[str, Any]
    review_summary: dict[str, Any]
    failure_summary: dict[str, Any]
    artifact_summary: dict[str, Any]
    generated_at: str
