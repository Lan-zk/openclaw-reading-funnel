from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import load_module

module = load_module("skills/run-review/run.py", "run_review")


def test_run_review_aggregates_step_manifests(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    source_dir = run_dir / "source-fetch"
    normalize_dir = run_dir / "candidate-normalize"
    source_dir.mkdir(parents=True)
    normalize_dir.mkdir(parents=True)
    source_manifest = {
        "schema_name": "step-manifest",
        "schema_version": "1.0.0",
        "generated_at": "2026-03-24T00:00:00Z",
        "produced_by_skill": "source-fetch",
        "run_id": "run-1",
        "step_name": "source-fetch",
        "step_status": "SUCCEEDED",
        "continue_recommended": True,
        "input_artifacts": [],
        "output_artifacts": [
            {
                "artifact_name": "raw-source-items",
                "path": "raw-source-items.json",
                "schema_name": "raw-source-items",
                "schema_version": "1.0.0",
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": True,
                "required_for_next": True
            }
        ],
        "counts": {},
        "issues": [],
        "payload": {
            "pipeline_version": "phase1.v1",
            "ruleset_version": "phase1.conservative.v1",
            "source_config_hash": "abc"
        }
    }
    normalize_manifest = dict(source_manifest)
    normalize_manifest["step_name"] = "candidate-normalize"
    normalize_manifest["produced_by_skill"] = "candidate-normalize"
    (source_dir / "step-manifest.json").write_text(json.dumps(source_manifest), encoding="utf-8")
    (normalize_dir / "step-manifest.json").write_text(json.dumps(normalize_manifest), encoding="utf-8")
    result = module.build_run_review("run-1", run_dir, run_dir / "run-review")
    assert result["run_manifest"]["run_status"] == "SUCCEEDED"
    assert len(result["run_manifest"]["step_results"]) == 2
