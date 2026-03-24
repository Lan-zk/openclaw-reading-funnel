from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import REPO_ROOT, load_module

module = load_module("skills/reading-candidate-build/run.py", "reading_candidate_build")


def test_reading_candidate_build_creates_candidates(tmp_path: Path) -> None:
    cluster_plan = REPO_ROOT / "tests/fixtures/pipeline/cluster-plan.json"
    candidate_items = REPO_ROOT / "tests/fixtures/pipeline/candidate-items.scored.json"
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.build_reading_candidates("fixture-run", cluster_plan, candidate_items, upstream_manifest, tmp_path / "out")
    assert result["reading_candidates"]["item_count"] == 2
    assert result["reading_candidates"]["items"][0]["needs_review"] is True
    assert result["step_manifest"]["step_status"] == "PARTIAL_SUCCESS"
