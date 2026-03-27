"""Reporting helpers for generate-long-cycle-assets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .models import (
    AuthorReviewItem,
    HotTopicSignal,
    LongCycleAsset,
    LongCycleFailureRecord,
    LongCycleReport,
    LongCycleStepManifest,
    LongCycleStepResult,
    LongSignal,
    PeriodAssetSet,
    TopicWritabilityAssessment,
)


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
    step_results: list[dict[str, Any] | LongCycleStepResult],
    failures: list[LongCycleFailureRecord],
) -> str:
    if any(_get_attr(step, "status") == STEP_FAILED for step in step_results):
        return WORKFLOW_FAILED
    if failures:
        return WORKFLOW_PARTIAL_SUCCESS
    return WORKFLOW_SUCCEEDED


def build_long_cycle_report(
    manifest: dict[str, Any] | LongCycleStepManifest,
    period_asset_set: PeriodAssetSet | None,
    hot_topics: list[HotTopicSignal],
    long_signals: list[LongSignal],
    topic_assessments: list[TopicWritabilityAssessment],
    assets: list[LongCycleAsset],
    review_items: list[AuthorReviewItem],
    failures: list[LongCycleFailureRecord],
    metrics: dict[str, Any],
    generated_at: str,
) -> LongCycleReport:
    asset_scope_counts = Counter(item.asset_scope for item in assets)
    review_scope_counts = Counter(item.review_scope for item in review_items)
    failure_type_counts = Counter(item.failure_type for item in failures)
    return LongCycleReport(
        run_id=_get_attr(manifest, "run_id"),
        workflow_status=_get_attr(manifest, "workflow_status"),
        period_summary={
            "period_id": period_asset_set.period_id if period_asset_set is not None else None,
            "knowledge_asset_count": len(period_asset_set.knowledge_asset_ids) if period_asset_set is not None else 0,
            "daily_review_issue_count": len(period_asset_set.daily_review_issue_ids) if period_asset_set is not None else 0,
            "period_start": period_asset_set.period_start if period_asset_set is not None else None,
            "period_end": period_asset_set.period_end if period_asset_set is not None else None,
        },
        signal_summary={
            "hot_topic_count": len(hot_topics),
            "long_signal_count": len(long_signals),
            "topic_assessment_count": len(topic_assessments),
        },
        asset_summary={
            "long_cycle_asset_count": len(assets),
            "by_scope": dict(asset_scope_counts),
        },
        review_summary={
            "author_review_item_count": len(review_items),
            "by_scope": dict(review_scope_counts),
        },
        failure_summary={
            "total_failures": len(failures),
            "by_type": dict(failure_type_counts),
        },
        artifact_summary={
            "artifact_paths": _get_attr(manifest, "artifact_paths"),
            "workflow_duration_ms": metrics.get("workflow_duration_ms", 0),
        },
        generated_at=generated_at,
    )


def render_long_cycle_report(report: LongCycleReport) -> str:
    lines = [
        "# generate-long-cycle-assets report",
        "",
        f"- run_id: `{report.run_id}`",
        f"- workflow_status: `{report.workflow_status}`",
        f"- generated_at: `{report.generated_at}`",
        "",
        "## Period Summary",
        "",
        f"- period_id: {report.period_summary.get('period_id')}",
        f"- knowledge_asset_count: {report.period_summary.get('knowledge_asset_count', 0)}",
        f"- daily_review_issue_count: {report.period_summary.get('daily_review_issue_count', 0)}",
        "",
        "## Signal Summary",
        "",
        f"- hot_topic_count: {report.signal_summary.get('hot_topic_count', 0)}",
        f"- long_signal_count: {report.signal_summary.get('long_signal_count', 0)}",
        f"- topic_assessment_count: {report.signal_summary.get('topic_assessment_count', 0)}",
        "",
        "## Asset Summary",
        "",
        f"- long_cycle_asset_count: {report.asset_summary.get('long_cycle_asset_count', 0)}",
        "",
        "## Review Summary",
        "",
        f"- author_review_item_count: {report.review_summary.get('author_review_item_count', 0)}",
        "",
        "## Failure Summary",
        "",
        f"- total_failures: {report.failure_summary.get('total_failures', 0)}",
    ]
    by_type = report.failure_summary.get("by_type", {})
    if by_type:
        lines.extend(["", "### Failure Types", ""])
        for key, value in sorted(by_type.items()):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


@dataclass(slots=True)
class StepRecorder:
    run_id: str
    workflow_name: str = "generate-long-cycle-assets"
    started_at: str | None = None
    step_results: list[LongCycleStepResult] = field(default_factory=list)

    def record(
        self,
        step_name: str,
        status: str,
        input_count: int,
        output_count: int,
        review_count: int,
        failure_count: int,
        started_at: str,
        finished_at: str,
    ) -> LongCycleStepResult:
        result = LongCycleStepResult(
            step_name=step_name,
            status=status,
            input_count=input_count,
            output_count=output_count,
            review_count=review_count,
            failure_count=failure_count,
            started_at=started_at,
            finished_at=finished_at,
        )
        self.step_results.append(result)
        return result

    def build_manifest(
        self,
        finished_at: str,
        failures: list[LongCycleFailureRecord],
        artifact_paths: dict[str, str],
    ) -> LongCycleStepManifest:
        return LongCycleStepManifest(
            run_id=self.run_id,
            workflow_name=self.workflow_name,
            step_results=self.step_results,
            started_at=self.started_at or finished_at,
            finished_at=finished_at,
            workflow_status=determine_workflow_status(self.step_results, failures),
            artifact_paths=artifact_paths,
        )


def _get_attr(item: dict[str, Any] | Any, key: str) -> Any:
    if isinstance(item, dict):
        return item[key]
    return getattr(item, key)
