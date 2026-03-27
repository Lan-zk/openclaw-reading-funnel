"""Object models for ingest-normalize."""

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
class SourceDescriptor(JsonModel):
    source_id: str
    source_name: str
    adapter_type: str
    enabled: bool
    fetch_policy: dict[str, Any]
    endpoint: str | None = None
    auth_ref: str | None = None
    tags: list[str] = field(default_factory=list)
    default_language: str | None = None
    adapter_config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceSyncPlan(JsonModel):
    source_id: str
    plan_id: str
    mode: str
    since: str | None
    until: str
    cursor: dict[str, Any] | None
    page_limit: int | None
    item_limit: int | None
    planned_at: str


@dataclass(slots=True)
class FetchedSourceBatch(JsonModel):
    source_id: str
    plan_id: str
    adapter_type: str
    fetch_window: dict[str, Any]
    raw_items: list[Any]
    raw_count: int
    next_cursor: dict[str, Any] | None
    fetched_at: str
    fetch_status: str


@dataclass(slots=True)
class RawFeedItem(JsonModel):
    source_id: str
    origin_item_id: str
    title: str | None
    url: str | None
    summary: str | None
    author: str | None
    published_at: str | None
    raw_payload: dict[str, Any]
    language: str | None = None


@dataclass(slots=True)
class SourceEntryDraft(JsonModel):
    source_adapter_type: str
    source_id: str
    source_name: str
    origin_item_id: str
    title: str | None
    url: str | None
    summary: str | None
    author: str | None
    published_at: str | None
    fetched_at: str
    raw_payload: dict[str, Any]


@dataclass(slots=True)
class SourceEntry(JsonModel):
    source_entry_id: str
    source_entry_snapshot_id: str
    source_adapter_type: str
    source_id: str
    source_name: str
    origin_item_id: str
    title: str | None
    url: str | None
    summary: str | None
    author: str | None
    published_at: str | None
    fetched_at: str
    raw_payload: dict[str, Any]
    run_id: str
    status: str


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
class IngestFailureRecord(JsonModel):
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
class IngestStepResult(JsonModel):
    step_name: str
    status: str
    input_count: int
    output_count: int
    failure_count: int
    started_at: str
    finished_at: str


@dataclass(slots=True)
class IngestStepManifest(JsonModel):
    run_id: str
    workflow_name: str
    step_results: list[IngestStepResult]
    started_at: str
    finished_at: str
    workflow_status: str
    artifact_paths: dict[str, str]


@dataclass(slots=True)
class IngestReport(JsonModel):
    run_id: str
    workflow_status: str
    source_summary: dict[str, Any]
    failure_summary: dict[str, Any]
    artifact_summary: dict[str, Any]
    generated_at: str
