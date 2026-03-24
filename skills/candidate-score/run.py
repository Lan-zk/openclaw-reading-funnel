from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0.0"
STEP_NAME = "candidate-score"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compute_freshness_score(published_at: str | None) -> int:
    dt = parse_iso8601(published_at)
    if dt is None:
        return 30
    age_hours = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 0)
    if age_hours <= 24:
        return 100
    if age_hours <= 72:
        return 80
    if age_hours <= 24 * 7:
        return 60
    return 30


def compute_quality_and_flags(item: dict[str, Any]) -> tuple[int, list[str], str]:
    score = 0
    flags: list[str] = []
    title = item.get("normalized_title") or item.get("title")
    canonical_url = item.get("canonical_url")
    summary = item.get("summary") or ""
    if title:
        score += 35
    else:
        flags.append("MISSING_TITLE")
    if canonical_url and urlparse(canonical_url).scheme in {"http", "https"}:
        score += 25
    else:
        flags.append("MISSING_URL")
        return score, flags, "FILTERED"
    if len(summary.strip()) >= 80:
        score += 15
    else:
        flags.append("SHORT_SUMMARY")
    if item.get("published_at"):
        score += 10
    else:
        flags.append("MISSING_PUBLISHED_AT")
    if item.get("source_name"):
        score += 10
    if item.get("author"):
        score += 5
    if not title:
        return score, flags, "FILTERED"
    return score, flags, "KEPT"


def run_score(run_id: str, input_path: Path, upstream_manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    upstream = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    if not upstream["continue_recommended"]:
        raise ValueError("Upstream manifest does not allow continuation.")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    scored_items: list[dict[str, Any]] = []
    kept_count = 0
    for item in payload["items"]:
        score, flags, filter_status = compute_quality_and_flags(item)
        scored = dict(item)
        scored["quality_score"] = min(score, 100)
        scored["freshness_score"] = compute_freshness_score(item.get("published_at"))
        scored["noise_flags"] = flags
        scored["filter_status"] = filter_status
        scored_items.append(scored)
        if filter_status == "KEPT":
            kept_count += 1
    output_dir.mkdir(parents=True, exist_ok=True)
    scored_path = output_dir / "candidate-items.scored.json"
    manifest_path = output_dir / "step-manifest.json"
    scored_payload = {
        "schema_name": "candidate-items.scored",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "item_count": len(scored_items),
        "items": scored_items,
    }
    dump_json(scored_path, scored_payload)
    manifest_payload = {
        "schema_name": "step-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "SUCCEEDED",
        "continue_recommended": kept_count > 0,
        "input_artifacts": [
            {
                "artifact_name": "candidate-items.normalized",
                "path": str(input_path),
                "schema_name": payload["schema_name"],
                "schema_version": payload["schema_version"],
                "required": True
            }
        ],
        "output_artifacts": [
            {
                "artifact_name": "candidate-items.scored",
                "path": str(scored_path),
                "schema_name": "candidate-items.scored",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": kept_count > 0,
                "required_for_next": True
            }
        ],
        "counts": {"item_count": len(scored_items), "kept_count": kept_count, "filtered_count": len(scored_items) - kept_count},
        "issues": [],
        "payload": {}
    }
    dump_json(manifest_path, manifest_payload)
    return {"scored": scored_payload, "step_manifest": manifest_payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--upstream-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_score(args.run_id, Path(args.input), Path(args.upstream_manifest), Path(args.output_dir))


if __name__ == "__main__":
    main()
