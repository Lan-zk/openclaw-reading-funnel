from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import REPO_ROOT, load_module

module = load_module("skills/dedup-cluster/run.py", "dedup_cluster")


def test_dedup_cluster_creates_singletons_for_non_matches(tmp_path: Path) -> None:
    scored_items = REPO_ROOT / "tests/fixtures/pipeline/candidate-items.scored.json"
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_cluster("fixture-run", scored_items, upstream_manifest, tmp_path / "out")
    assert result["cluster_plan"]["item_count"] == 3
    assert any(cluster["cluster_type"] == "SINGLETON" for cluster in result["cluster_plan"]["items"])


def test_dedup_cluster_marks_high_similarity_for_same_host_titles(tmp_path: Path) -> None:
    payload = json.loads((REPO_ROOT / "tests/fixtures/pipeline/candidate-items.scored.json").read_text(encoding="utf-8"))
    payload["items"][1]["canonical_url"] = "https://example.com/articles/openai-api-guide-v2"
    payload["items"][1]["source_name"] = "Example Tech Mirror"
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    upstream_manifest = tmp_path / "upstream.json"
    upstream_manifest.write_text(json.dumps({"continue_recommended": True}), encoding="utf-8")
    result = module.run_cluster("fixture-run", source, upstream_manifest, tmp_path / "out")
    assert any(cluster["cluster_type"] == "HIGH_SIMILARITY" and cluster["needs_review"] for cluster in result["cluster_plan"]["items"])
