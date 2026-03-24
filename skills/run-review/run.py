from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
STEP_NAME = "run-review"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_run_review(run_id: str, run_dir: Path, output_dir: Path) -> dict[str, Any]:
    step_results: list[dict[str, Any]] = []
    artifact_index: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    source_config_hash = ""
    pipeline_version = "phase1.v1"
    ruleset_version = "phase1.conservative.v1"
    manifests = sorted(run_dir.glob("*/step-manifest.json"))
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        step_results.append(
            {
                "step_name": manifest["step_name"],
                "step_status": manifest["step_status"],
                "continue_recommended": manifest["continue_recommended"],
                "step_manifest_path": str(manifest_path)
            }
        )
        artifact_index.extend(
            {
                "artifact_name": artifact["artifact_name"],
                "path": artifact["path"],
                "produced_by_skill": manifest["step_name"],
                "schema_name": artifact["schema_name"],
                "schema_version": artifact["schema_version"],
                "artifact_role": artifact["artifact_role"],
                "consumable_by_downstream": artifact["consumable_by_downstream"],
                "required_for_next": artifact["required_for_next"]
            }
            for artifact in manifest["output_artifacts"]
        )
        issues.extend(manifest.get("issues", []))
        payload = manifest.get("payload", {})
        if manifest["step_name"] == "source-fetch":
            source_config_hash = payload.get("source_config_hash", source_config_hash)
            pipeline_version = payload.get("pipeline_version", pipeline_version)
            ruleset_version = payload.get("ruleset_version", ruleset_version)
    primary_consumable = any(
        artifact["artifact_role"] == "PRIMARY" and artifact["consumable_by_downstream"]
        for artifact in artifact_index
    )
    step_statuses = [item["step_status"] for item in step_results]
    if step_results and all(status == "SUCCEEDED" for status in step_statuses) and primary_consumable:
        run_status = "SUCCEEDED"
    elif primary_consumable and any(status == "PARTIAL_SUCCESS" for status in step_statuses):
        run_status = "PARTIAL_SUCCESS"
    else:
        run_status = "FAILED"

    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest_path = output_dir / "run-manifest.json"
    run_review_path = output_dir / "run-review.json"
    run_report_path = output_dir / "run-report.md"
    run_manifest = {
        "schema_name": "run-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "run_status": run_status,
        "pipeline_version": pipeline_version,
        "ruleset_version": ruleset_version,
        "source_config_hash": source_config_hash,
        "step_results": step_results,
        "artifact_index": artifact_index,
        "counts": {"step_count": len(step_results), "artifact_count": len(artifact_index)},
        "issues": issues
    }
    run_review = {
        "schema_name": "run-review",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": run_status,
        "continue_recommended": False,
        "input_artifacts": [
            {
                "artifact_name": "step-manifests",
                "path": str(run_dir),
                "schema_name": "step-manifest",
                "schema_version": SCHEMA_VERSION,
                "required": True
            }
        ],
        "output_artifacts": [
            {
                "artifact_name": "run-manifest",
                "path": str(run_manifest_path),
                "schema_name": "run-manifest",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": True,
                "required_for_next": True
            },
            {
                "artifact_name": "run-review",
                "path": str(run_review_path),
                "schema_name": "run-review",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "FAILURE_REPORT",
                "consumable_by_downstream": True,
                "required_for_next": False
            },
            {
                "artifact_name": "run-report",
                "path": str(run_report_path),
                "schema_name": "run-report",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "HUMAN_REPORT",
                "consumable_by_downstream": False,
                "required_for_next": False
            }
        ],
        "counts": run_manifest["counts"],
        "issues": issues,
        "payload": {"run_status": run_status}
    }
    dump_json(run_manifest_path, run_manifest)
    dump_json(run_review_path, run_review)
    run_report_path.write_text(
        "# Run Report\n\n"
        f"- Run ID: {run_id}\n"
        f"- Run Status: {run_status}\n"
        f"- Step Count: {len(step_results)}\n"
        f"- Artifact Count: {len(artifact_index)}\n",
        encoding="utf-8"
    )
    return {"run_manifest": run_manifest, "run_review": run_review}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_run_review(args.run_id, Path(args.run_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
