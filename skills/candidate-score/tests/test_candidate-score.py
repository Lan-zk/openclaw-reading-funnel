from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import REPO_ROOT, load_module

module = load_module("skills/candidate-score/run.py", "candidate_score")


def test_candidate_score_scores_and_keeps_valid_items(tmp_path: Path) -> None:
    normalized_items = REPO_ROOT / "tests/fixtures/pipeline/candidate-items.normalized.json"
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_score("fixture-run", normalized_items, upstream_manifest, tmp_path / "out")
    first = result["scored"]["items"][0]
    assert first["filter_status"] == "KEPT"
    assert first["quality_score"] >= 85
    assert result["step_manifest"]["continue_recommended"] is True


def test_candidate_score_filters_missing_url(tmp_path: Path) -> None:
    payload = json.loads((REPO_ROOT / "tests/fixtures/pipeline/candidate-items.normalized.json").read_text(encoding="utf-8"))
    payload["items"][0]["canonical_url"] = None
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_score("fixture-run", source, upstream_manifest, tmp_path / "out")
    assert result["scored"]["items"][0]["filter_status"] == "FILTERED"
    assert "MISSING_URL" in result["scored"]["items"][0]["noise_flags"]
