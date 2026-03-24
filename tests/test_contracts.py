from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from tests.conftest import REPO_ROOT


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_collection_payloads_match_schemas() -> None:
    fixtures = [
        ("tests/fixtures/pipeline/raw-source-items.json", "schemas/raw-source-items.schema.json"),
        ("tests/fixtures/pipeline/candidate-items.normalized.json", "schemas/candidate-items.normalized.schema.json"),
        ("tests/fixtures/pipeline/candidate-items.scored.json", "schemas/candidate-items.scored.schema.json"),
        ("tests/fixtures/pipeline/cluster-plan.json", "schemas/cluster-plan.schema.json")
    ]
    for payload_rel, schema_rel in fixtures:
        jsonschema.validate(_load_json(REPO_ROOT / payload_rel), _load_json(REPO_ROOT / schema_rel))
