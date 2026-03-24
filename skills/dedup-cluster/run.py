from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0.0"
STEP_NAME = "dedup-cluster"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def title_tokens(title: str | None) -> set[str]:
    if not title:
        return set()
    return {part for part in re.split(r"[^a-z0-9]+", title.lower()) if part}


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def make_cluster(cluster_id: str, items: list[dict[str, Any]], cluster_type: str, confidence: float, merge_reason: str, needs_review: bool) -> dict[str, Any]:
    ranked = sorted(
        items,
        key=lambda item: (
            -(item.get("quality_score") or 0),
            -(parse_iso8601(item.get("published_at")) or datetime.fromtimestamp(0, tz=timezone.utc)).timestamp(),
            item["candidate_item_id"]
        )
    )
    return {
        "cluster_id": cluster_id,
        "candidate_item_ids": [item["candidate_item_id"] for item in items],
        "primary_candidate_item_id": ranked[0]["candidate_item_id"],
        "cluster_type": cluster_type,
        "cluster_confidence": confidence,
        "merge_reason": merge_reason,
        "needs_review": needs_review
    }


def run_cluster(run_id: str, input_path: Path, upstream_manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    upstream = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    if not upstream["continue_recommended"]:
        raise ValueError("Upstream manifest does not allow continuation.")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    kept_items = [item for item in payload["items"] if item.get("filter_status") == "KEPT"]
    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in kept_items:
        exact_key = item.get("canonical_url") or item.get("url_fingerprint") or item["candidate_item_id"]
        exact_groups[exact_key].append(item)

    clusters: list[dict[str, Any]] = []
    singletons: list[dict[str, Any]] = []
    cluster_index = 1
    for _, items in exact_groups.items():
        if len(items) > 1:
            clusters.append(make_cluster(f"cluster-{cluster_index}", items, "EXACT_DUPLICATE", 1.0, "Items share the same canonical URL or URL fingerprint.", False))
            cluster_index += 1
        else:
            singletons.extend(items)

    used: set[str] = set()
    for item in sorted(singletons, key=lambda entry: entry["candidate_item_id"]):
        if item["candidate_item_id"] in used:
            continue
        hostname = urlparse(item.get("canonical_url") or "").hostname
        item_tokens = title_tokens(item.get("normalized_title") or item.get("title"))
        item_time = parse_iso8601(item.get("published_at"))
        similar_group = [item]
        for candidate in singletons:
            if candidate["candidate_item_id"] == item["candidate_item_id"] or candidate["candidate_item_id"] in used:
                continue
            other_hostname = urlparse(candidate.get("canonical_url") or "").hostname
            if hostname != other_hostname:
                continue
            other_time = parse_iso8601(candidate.get("published_at"))
            if item_time is None or other_time is None or abs((item_time - other_time).total_seconds()) > 24 * 3600:
                continue
            similarity = jaccard_similarity(item_tokens, title_tokens(candidate.get("normalized_title") or candidate.get("title")))
            if similarity >= 0.90:
                similar_group.append(candidate)
        for candidate in similar_group:
            used.add(candidate["candidate_item_id"])
        if len(similar_group) > 1:
            clusters.append(make_cluster(f"cluster-{cluster_index}", similar_group, "HIGH_SIMILARITY", 0.8, "Same hostname, close publication time, and highly similar titles.", True))
        else:
            clusters.append(make_cluster(f"cluster-{cluster_index}", similar_group, "SINGLETON", 1.0, "No exact or high-similarity match found.", False))
        cluster_index += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    cluster_plan_path = output_dir / "cluster-plan.json"
    cluster_review_json_path = output_dir / "cluster-review.json"
    cluster_review_md_path = output_dir / "cluster-review-report.md"
    manifest_path = output_dir / "step-manifest.json"
    review_clusters = [cluster for cluster in clusters if cluster["needs_review"]]
    cluster_plan_payload = {
        "schema_name": "cluster-plan",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "item_count": len(clusters),
        "items": clusters
    }
    review_payload = {
        "schema_name": "cluster-review",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "PARTIAL_SUCCESS" if review_clusters else "SUCCEEDED",
        "continue_recommended": len(clusters) > 0,
        "input_artifacts": [],
        "output_artifacts": [],
        "counts": {"cluster_count": len(clusters), "review_count": len(review_clusters)},
        "issues": [{"code": "LOW_CONFIDENCE_CLUSTER", "message": cluster["cluster_id"]} for cluster in review_clusters],
        "payload": {"review_clusters": review_clusters}
    }
    dump_json(cluster_plan_path, cluster_plan_payload)
    dump_json(cluster_review_json_path, review_payload)
    cluster_review_md_path.write_text(
        "# Cluster Review Report\n\n" + "\n".join(
            f"- {cluster['cluster_id']}: {cluster['merge_reason']}" for cluster in review_clusters
        ) + ("\n" if review_clusters else "- No review-needed clusters.\n"),
        encoding="utf-8"
    )
    manifest_payload = {
        "schema_name": "step-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": review_payload["step_status"],
        "continue_recommended": len(clusters) > 0,
        "input_artifacts": [
            {
                "artifact_name": "candidate-items.scored",
                "path": str(input_path),
                "schema_name": payload["schema_name"],
                "schema_version": payload["schema_version"],
                "required": True
            }
        ],
        "output_artifacts": [
            {
                "artifact_name": "cluster-plan",
                "path": str(cluster_plan_path),
                "schema_name": "cluster-plan",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": len(clusters) > 0,
                "required_for_next": True
            },
            {
                "artifact_name": "cluster-review",
                "path": str(cluster_review_json_path),
                "schema_name": "cluster-review",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "FAILURE_REPORT",
                "consumable_by_downstream": True,
                "required_for_next": False
            },
            {
                "artifact_name": "cluster-review-report",
                "path": str(cluster_review_md_path),
                "schema_name": "cluster-review-report",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "HUMAN_REPORT",
                "consumable_by_downstream": False,
                "required_for_next": False
            }
        ],
        "counts": review_payload["counts"],
        "issues": review_payload["issues"],
        "payload": {}
    }
    dump_json(manifest_path, manifest_payload)
    return {"cluster_plan": cluster_plan_payload, "cluster_review": review_payload, "step_manifest": manifest_payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--upstream-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_cluster(args.run_id, Path(args.input), Path(args.upstream_manifest), Path(args.output_dir))


if __name__ == "__main__":
    main()
