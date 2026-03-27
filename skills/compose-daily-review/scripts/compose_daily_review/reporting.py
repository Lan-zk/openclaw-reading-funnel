"""Reporting helpers for compose-daily-review."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .models import (
    DailyReviewFailureRecord,
    DailyReviewIssue,
    DailyReviewReport,
    DailyReviewStepManifest,
    DailyReviewStepResult,
    EditorialReviewItem,
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
    step_results: list[dict[str, Any] | DailyReviewStepResult],
    failures: list[DailyReviewFailureRecord],
) -> str:
    if any(_get_attr(step, "status") == STEP_FAILED for step in step_results):
        return WORKFLOW_FAILED
    if failures:
        return WORKFLOW_PARTIAL_SUCCESS
    return WORKFLOW_SUCCEEDED


def build_daily_review_report(
    manifest: dict[str, Any] | DailyReviewStepManifest,
    issues: list[DailyReviewIssue],
    review_items: list[EditorialReviewItem],
    failures: list[DailyReviewFailureRecord],
    metrics: dict[str, Any],
    generated_at: str,
) -> DailyReviewReport:
    issue = issues[0] if issues else None
    section_counts = {section: len(entries) for section, entries in (issue.sections.items() if issue else {})}
    review_flag_counts = Counter(flag for item in review_items for flag in item.review_flags)
    failure_type_counts = Counter(item.failure_type for item in failures)
    return DailyReviewReport(
        run_id=_get_attr(manifest, "run_id"),
        workflow_status=_get_attr(manifest, "workflow_status"),
        issue_summary={
            "issue_count": len(issues),
            "section_entry_count": sum(section_counts.values()),
            "sections": section_counts,
            "top_theme_count": len(issue.top_themes) if issue else 0,
        },
        review_summary={
            "review_item_count": len(review_items),
            "by_flag": dict(review_flag_counts),
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


def render_daily_review_report(report: DailyReviewReport) -> str:
    lines = [
        "# compose-daily-review report",
        "",
        f"- run_id: `{report.run_id}`",
        f"- workflow_status: `{report.workflow_status}`",
        f"- generated_at: `{report.generated_at}`",
        "",
        "## Issue Summary",
        "",
        f"- issue_count: {report.issue_summary.get('issue_count', 0)}",
        f"- section_entry_count: {report.issue_summary.get('section_entry_count', 0)}",
        f"- top_theme_count: {report.issue_summary.get('top_theme_count', 0)}",
        "",
        "## Review Summary",
        "",
        f"- review_item_count: {report.review_summary.get('review_item_count', 0)}",
    ]
    by_flag = report.review_summary.get("by_flag", {})
    if by_flag:
        lines.extend(["", "### Review Flags", ""])
        for key, value in sorted(by_flag.items()):
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Failure Summary", "", f"- total_failures: {report.failure_summary.get('total_failures', 0)}"])
    by_type = report.failure_summary.get("by_type", {})
    if by_type:
        lines.extend(["", "### Failure Types", ""])
        for key, value in sorted(by_type.items()):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


@dataclass(slots=True)
class StepRecorder:
    run_id: str
    workflow_name: str = "compose-daily-review"
    started_at: str | None = None
    step_results: list[DailyReviewStepResult] = field(default_factory=list)

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
    ) -> DailyReviewStepResult:
        result = DailyReviewStepResult(
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
        failures: list[DailyReviewFailureRecord],
        artifact_paths: dict[str, str],
    ) -> DailyReviewStepManifest:
        return DailyReviewStepManifest(
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
