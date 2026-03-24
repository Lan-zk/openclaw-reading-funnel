from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

SCHEMA_VERSION = "1.0.0"
STEP_NAME = "candidate-normalize"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_title(title: str | None) -> str | None:
    if title is None:
        return None
    compact = re.sub(r"\s+", " ", title).strip()
    return compact or None


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    filtered_query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.params,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def detect_language(title: str | None, summary: str | None) -> str:
    text = f"{title or ''} {summary or ''}"
    zh_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_count = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if zh_count > ascii_count:
        return "zh"
    if ascii_count > 0:
        return "en"
    return "unknown"


def build_candidate(raw_item: dict[str, Any], run_id: str) -> dict[str, Any]:
    raw_item_id = raw_item["raw_item_id"]
    canonical_url = canonicalize_url(raw_item.get("url"))
    return {
        "candidate_item_id": sha256_text(raw_item_id)[:16],
        "origin_raw_item_id": raw_item_id,
        "source_adapter_type": raw_item.get("source_adapter_type", "unknown"),
        "source_id": raw_item.get("source_id"),
        "source_name": raw_item.get("source_name"),
        "canonical_url": canonical_url,
        "url_fingerprint": sha256_text(canonical_url)[:16] if canonical_url else None,
        "title": raw_item.get("title"),
        "normalized_title": normalize_title(raw_item.get("title")),
        "summary": raw_item.get("summary"),
        "published_at": raw_item.get("published_at"),
        "language": detect_language(raw_item.get("title"), raw_item.get("summary")),
        "normalize_status": "NORMALIZED",
        "freshness_score": None,
        "quality_score": None,
        "noise_flags": [],
        "filter_status": "KEPT",
        "dedup_key": None,
        "run_id": run_id,
        "author": raw_item.get("author")
    }


def run_normalize(run_id: str, input_path: Path, upstream_manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    upstream = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    if not upstream["continue_recommended"]:
        raise ValueError("Upstream manifest does not allow continuation.")
    raw_items_payload = json.loads(input_path.read_text(encoding="utf-8"))
    failures: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for item in raw_items_payload["items"]:
        if not item.get("raw_item_id"):
            failures.append({"reason": "MISSING_RAW_ITEM_ID", "item": item})
            continue
        candidates.append(build_candidate(item, run_id))
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = output_dir / "candidate-items.normalized.json"
    failures_path = output_dir / "normalization-failures.json"
    manifest_path = output_dir / "step-manifest.json"
    normalized_payload = {
        "schema_name": "candidate-items.normalized",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "item_count": len(candidates),
        "items": candidates,
    }
    failures_payload = {
        "schema_name": "normalization-failures",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "PARTIAL_SUCCESS" if failures else "SUCCEEDED",
        "continue_recommended": len(candidates) > 0,
        "input_artifacts": [],
        "output_artifacts": [],
        "counts": {"normalized_count": len(candidates), "failure_count": len(failures)},
        "issues": [{"code": failure["reason"], "message": failure["reason"]} for failure in failures],
        "payload": {"failures": failures},
    }
    dump_json(normalized_path, normalized_payload)
    dump_json(failures_path, failures_payload)
    manifest_payload = {
        "schema_name": "step-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "PARTIAL_SUCCESS" if failures else "SUCCEEDED",
        "continue_recommended": len(candidates) > 0,
        "input_artifacts": [
            {
                "artifact_name": "raw-source-items",
                "path": str(input_path),
                "schema_name": raw_items_payload["schema_name"],
                "schema_version": raw_items_payload["schema_version"],
                "required": True,
            }
        ],
        "output_artifacts": [
            {
                "artifact_name": "candidate-items.normalized",
                "path": str(normalized_path),
                "schema_name": "candidate-items.normalized",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": len(candidates) > 0,
                "required_for_next": True,
            },
            {
                "artifact_name": "normalization-failures",
                "path": str(failures_path),
                "schema_name": "normalization-failures",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "FAILURE_REPORT",
                "consumable_by_downstream": True,
                "required_for_next": False,
            }
        ],
        "counts": failures_payload["counts"],
        "issues": failures_payload["issues"],
        "payload": {}
    }
    dump_json(manifest_path, manifest_payload)
    return {"normalized": normalized_payload, "failures": failures_payload, "step_manifest": manifest_payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--upstream-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_normalize(args.run_id, Path(args.input), Path(args.upstream_manifest), Path(args.output_dir))


if __name__ == "__main__":
    main()
