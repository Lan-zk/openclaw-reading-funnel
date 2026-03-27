"""Reporting helpers for curate-retain."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


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


def determine_workflow_status(step_results: list[dict[str, Any]], failures: list[dict[str, Any]]) -> str:
    if any(step["status"] == STEP_FAILED for step in step_results):
        return WORKFLOW_FAILED
    if failures:
        return WORKFLOW_PARTIAL_SUCCESS
    return WORKFLOW_SUCCEEDED


def build_curation_report(
    manifest: dict[str, Any],
    queue_items: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    metrics: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    queue_reason_counts = Counter(reason for item in queue_items for reason in item.get("queue_reason", []))
    decision_counts = Counter(item["decision"] for item in decisions)
    asset_type_counts = Counter(item["asset_type"] for item in assets)
    signal_type_counts = Counter(item["signal_type"] for item in signals)
    failure_type_counts = Counter(item["failure_type"] for item in failures)
    return {
        "run_id": manifest["run_id"],
        "workflow_status": manifest["workflow_status"],
        "queue_summary": {
            "queue_item_count": len(queue_items),
            "by_priority": dict(Counter(item["queue_priority"] for item in queue_items)),
            "by_reason": dict(queue_reason_counts),
        },
        "decision_summary": {
            "retention_decision_count": len(decisions),
            "by_decision": dict(decision_counts),
        },
        "asset_summary": {
            "knowledge_asset_count": len(assets),
            "by_asset_type": dict(asset_type_counts),
        },
        "signal_summary": {
            "preference_signal_count": len(signals),
            "by_signal_type": dict(signal_type_counts),
        },
        "failure_summary": {
            "total_failures": len(failures),
            "by_type": dict(failure_type_counts),
        },
        "artifact_summary": {
            "artifact_paths": manifest["artifact_paths"],
            "workflow_duration_ms": metrics.get("workflow_duration_ms", 0),
        },
        "generated_at": generated_at,
    }


def render_curation_report(report: dict[str, Any]) -> str:
    lines = [
        "# curate-retain report",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- workflow_status: `{report['workflow_status']}`",
        f"- generated_at: `{report['generated_at']}`",
        "",
        "## Queue Summary",
        "",
        f"- queue_item_count: {report['queue_summary'].get('queue_item_count', 0)}",
        "",
        "## Decision Summary",
        "",
        f"- retention_decision_count: {report['decision_summary'].get('retention_decision_count', 0)}",
        "",
        "## Asset Summary",
        "",
        f"- knowledge_asset_count: {report['asset_summary'].get('knowledge_asset_count', 0)}",
        "",
        "## Signal Summary",
        "",
        f"- preference_signal_count: {report['signal_summary'].get('preference_signal_count', 0)}",
        "",
        "## Failure Summary",
        "",
        f"- total_failures: {report['failure_summary'].get('total_failures', 0)}",
    ]
    by_type = report["failure_summary"].get("by_type", {})
    if by_type:
        lines.extend(["", "### Failure Types", ""])
        for key, value in sorted(by_type.items()):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


@dataclass(slots=True)
class StepRecorder:
    run_id: str
    workflow_name: str = "curate-retain"
    started_at: str | None = None
    step_results: list[dict[str, Any]] = field(default_factory=list)

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
    ) -> dict[str, Any]:
        result = {
            "step_name": step_name,
            "status": status,
            "input_count": input_count,
            "output_count": output_count,
            "review_count": review_count,
            "failure_count": failure_count,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        self.step_results.append(result)
        return result

    def build_manifest(
        self,
        finished_at: str,
        failures: list[dict[str, Any]],
        artifact_paths: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "step_results": self.step_results,
            "started_at": self.started_at or finished_at,
            "finished_at": finished_at,
            "workflow_status": determine_workflow_status(self.step_results, failures),
            "artifact_paths": artifact_paths,
        }
