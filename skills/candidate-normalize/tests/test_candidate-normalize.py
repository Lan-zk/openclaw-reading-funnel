from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import REPO_ROOT, load_module

module = load_module("skills/candidate-normalize/run.py", "candidate_normalize")


def test_candidate_normalize_creates_candidates_and_manifest(tmp_path: Path) -> None:
    raw_items = REPO_ROOT / "tests/fixtures/pipeline/raw-source-items.json"
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_normalize("fixture-run", raw_items, upstream_manifest, tmp_path / "out")
    assert result["normalized"]["item_count"] == 3
    assert result["step_manifest"]["continue_recommended"] is True
    assert result["normalized"]["items"][0]["canonical_url"] == "https://example.com/articles/openai-api"


def test_candidate_normalize_records_failure_for_missing_raw_id(tmp_path: Path) -> None:
    broken_payload = json.loads((REPO_ROOT / "tests/fixtures/pipeline/raw-source-items.json").read_text(encoding="utf-8"))
    broken_payload["items"][0]["raw_item_id"] = ""
    broken_path = tmp_path / "broken.json"
    broken_path.write_text(json.dumps(broken_payload), encoding="utf-8")
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_normalize("fixture-run", broken_path, upstream_manifest, tmp_path / "out")
    assert result["normalized"]["item_count"] == 2
    assert result["failures"]["counts"]["failure_count"] == 1
    assert result["step_manifest"]["step_status"] == "PARTIAL_SUCCESS"
