"""Reporting helpers for ingest-normalize."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .models import IngestFailureRecord, IngestReport, IngestStepManifest, IngestStepResult


STEP_SUCCESS_WITH_OUTPUT = "SUCCESS_WITH_OUTPUT"
STEP_SUCCESS_EMPTY = "SUCCESS_EMPTY"
STEP_FAILED = "FAILED"

WORKFLOW_SUCCEEDED = "SUCCEEDED"
WORKFLOW_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
WORKFLOW_FAILED = "FAILED"


def determine_step_status(output_count: int, failed: bool = False) -> str:
    if failed:
        return STEP_FAILED
    if output_count > 0:
        return STEP_SUCCESS_WITH_OUTPUT
    return STEP_SUCCESS_EMPTY


def determine_workflow_status(
    step_results: list[dict[str, Any] | IngestStepResult],
    failures: list[IngestFailureRecord],
) -> str:
    if any(_get_attr(step, "status") == STEP_FAILED for step in step_results):
        return WORKFLOW_FAILED
    if failures:
        return WORKFLOW_PARTIAL_SUCCESS
    return WORKFLOW_SUCCEEDED


def build_ingest_report(
    manifest: dict[str, Any] | IngestStepManifest,
    failures: list[IngestFailureRecord],
    metrics: dict[str, Any],
    generated_at: str,
) -> IngestReport:
    run_id = _get_attr(manifest, "run_id")
    workflow_status = _get_attr(manifest, "workflow_status")
    artifact_paths = _get_attr(manifest, "artifact_paths")
    failure_type_counts = Counter(item.failure_type for item in failures)
    source_scope_counts = Counter(item.scope_type for item in failures)
    source_summary = {
        "source_discovery_count": metrics.get("source_discovery_count", 0),
        "source_enabled_count": metrics.get("source_enabled_count", 0),
        "source_fetch_success_count": metrics.get("source_fetch_success_count", 0),
        "source_fetch_empty_count": metrics.get("source_fetch_empty_count", 0),
        "source_fetch_failed_count": metrics.get("source_fetch_failed_count", 0),
        "raw_feed_item_count": metrics.get("raw_feed_item_count", 0),
        "source_entry_count": metrics.get("source_entry_count", 0),
        "normalized_candidate_count": metrics.get("normalized_candidate_count", 0),
    }
    failure_summary = {
        "total_failures": len(failures),
        "by_type": dict(failure_type_counts),
        "by_scope_type": dict(source_scope_counts),
    }
    artifact_summary = {
        "artifact_paths": artifact_paths,
        "failure_record_count": len(failures),
        "workflow_duration_ms": metrics.get("workflow_duration_ms", 0),
    }
    return IngestReport(
        run_id=run_id,
        workflow_status=workflow_status,
        source_summary=source_summary,
        failure_summary=failure_summary,
        artifact_summary=artifact_summary,
        generated_at=generated_at,
    )


@dataclass(slots=True)
class StepRecorder:
    run_id: str
    workflow_name: str = "ingest-normalize"
    started_at: str | None = None
    step_results: list[IngestStepResult] = field(default_factory=list)

    def record(
        self,
        step_name: str,
        status: str,
        input_count: int,
        output_count: int,
        failure_count: int,
        started_at: str,
        finished_at: str,
    ) -> IngestStepResult:
        result = IngestStepResult(
            step_name=step_name,
            status=status,
            input_count=input_count,
            output_count=output_count,
            failure_count=failure_count,
            started_at=started_at,
            finished_at=finished_at,
        )
        self.step_results.append(result)
        return result

    def build_manifest(
        self,
        finished_at: str,
        failures: list[IngestFailureRecord],
        artifact_paths: dict[str, str],
    ) -> IngestStepManifest:
        return IngestStepManifest(
            run_id=self.run_id,
            workflow_name=self.workflow_name,
            step_results=self.step_results,
            started_at=self.started_at or finished_at,
            finished_at=finished_at,
            workflow_status=determine_workflow_status(self.step_results, failures),
            artifact_paths=artifact_paths,
        )


def _get_attr(obj: dict[str, Any] | Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)
