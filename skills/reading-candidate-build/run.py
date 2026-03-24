from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
STEP_NAME = "reading-candidate-build"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_reading_candidates(run_id: str, cluster_plan_path: Path, candidate_items_path: Path, upstream_manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    upstream = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    if not upstream["continue_recommended"]:
        raise ValueError("Upstream manifest does not allow continuation.")
    cluster_plan = json.loads(cluster_plan_path.read_text(encoding="utf-8"))
    candidate_items = json.loads(candidate_items_path.read_text(encoding="utf-8"))
    candidate_map = {item["candidate_item_id"]: item for item in candidate_items["items"]}
    reading_candidates: list[dict[str, Any]] = []
    for cluster in cluster_plan["items"]:
        members = [candidate_map[item_id] for item_id in cluster["candidate_item_ids"]]
        primary = sorted(
            members,
            key=lambda item: (-(item.get("quality_score") or 0), -parse_iso8601(item.get("published_at")).timestamp(), item["candidate_item_id"])
        )[0]
        published_times = [item.get("published_at") for item in members if item.get("published_at")]
        reading_candidates.append(
            {
                "reading_candidate_id": f"{run_id}:{cluster['cluster_id']}",
                "candidate_item_ids": [item["candidate_item_id"] for item in members],
                "primary_candidate_item_id": primary["candidate_item_id"],
                "cluster_type": cluster["cluster_type"],
                "cluster_confidence": cluster["cluster_confidence"],
                "canonical_url": primary.get("canonical_url"),
                "display_title": primary.get("normalized_title") or primary.get("title"),
                "display_summary": primary.get("summary"),
                "source_count": len(members),
                "published_at_range": {
                    "start": min(published_times) if published_times else None,
                    "end": max(published_times) if published_times else None
                },
                "aggregate_score": max(item.get("quality_score") or 0 for item in members),
                "merge_reason": cluster["merge_reason"],
                "needs_review": cluster["needs_review"],
                "run_id": run_id
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    reading_candidates_path = output_dir / "reading-candidates.json"
    manifest_path = output_dir / "step-manifest.json"
    payload = {
        "schema_name": "reading-candidates",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "item_count": len(reading_candidates),
        "items": reading_candidates
    }
    dump_json(reading_candidates_path, payload)
    manifest = {
        "schema_name": "step-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "PARTIAL_SUCCESS" if any(item["needs_review"] for item in reading_candidates) else "SUCCEEDED",
        "continue_recommended": len(reading_candidates) > 0,
        "input_artifacts": [
            {
                "artifact_name": "cluster-plan",
                "path": str(cluster_plan_path),
                "schema_name": cluster_plan["schema_name"],
                "schema_version": cluster_plan["schema_version"],
                "required": True
            },
            {
                "artifact_name": "candidate-items.scored",
                "path": str(candidate_items_path),
                "schema_name": candidate_items["schema_name"],
                "schema_version": candidate_items["schema_version"],
                "required": True
            }
        ],
        "output_artifacts": [
            {
                "artifact_name": "reading-candidates",
                "path": str(reading_candidates_path),
                "schema_name": "reading-candidates",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": len(reading_candidates) > 0,
                "required_for_next": True
            }
        ],
        "counts": {"item_count": len(reading_candidates), "review_count": sum(1 for item in reading_candidates if item["needs_review"])},
        "issues": [{"code": "NEEDS_REVIEW", "message": item["reading_candidate_id"]} for item in reading_candidates if item["needs_review"]],
        "payload": {}
    }
    dump_json(manifest_path, manifest)
    return {"reading_candidates": payload, "step_manifest": manifest}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cluster-plan", required=True)
    parser.add_argument("--candidate-items", required=True)
    parser.add_argument("--upstream-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_reading_candidates(args.run_id, Path(args.cluster_plan), Path(args.candidate_items), Path(args.upstream_manifest), Path(args.output_dir))


if __name__ == "__main__":
    main()
