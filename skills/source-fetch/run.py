from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

SCHEMA_VERSION = "1.0.0"
PIPELINE_VERSION = "phase1.v1"
RULESET_VERSION = "phase1.conservative.v1"
STEP_NAME = "source-fetch"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_api_base(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    return cleaned if cleaned.endswith("api/greader.php") else f"{cleaned}/api/greader.php"


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


def build_raw_item(item: dict[str, Any], run_id: str, fetched_at: str) -> dict[str, Any]:
    origin = item.get("origin") or {}
    alternate = item.get("alternate") or []
    url = alternate[0].get("href") if alternate else None
    canonical_url = canonicalize_url(url)
    origin_item_id = item.get("id")
    source_id = origin.get("streamId")
    title = item.get("title")
    published = item.get("published")
    published_at = None
    if published is not None:
        published_at = datetime.fromtimestamp(int(published), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    raw_item_id = origin_item_id
    if not raw_item_id and source_id and canonical_url:
        raw_item_id = sha256_text(f"{source_id}|{canonical_url}")
    if not raw_item_id:
        raw_item_id = sha256_text(f"{source_id}|{title or ''}|{published_at or ''}")
    summary = None
    summary_obj = item.get("summary")
    if isinstance(summary_obj, dict):
        summary = summary_obj.get("content")
    return {
        "raw_item_id": raw_item_id,
        "source_adapter_type": "freshrss",
        "source_id": source_id,
        "source_name": origin.get("title"),
        "origin_item_id": origin_item_id,
        "title": title,
        "url": url,
        "summary": summary,
        "author": item.get("author"),
        "published_at": published_at,
        "fetched_at": fetched_at,
        "raw_payload": item,
        "run_id": run_id,
    }


def client_login(client: httpx.Client, api_base: str, username: str, password: str) -> str | None:
    response = client.post(f"{api_base}/accounts/ClientLogin", data={"Email": username, "Passwd": password})
    if response.status_code >= 400:
        return None
    for line in response.text.splitlines():
        if line.startswith("Auth="):
            return line.split("=", 1)[1].strip()
    return None


def fetch_stream_response(client: httpx.Client, api_base: str, username: str, password: str, limit_per_run: int) -> dict[str, Any]:
    token = client_login(client, api_base, username, password)
    params = {"output": "json", "n": str(limit_per_run)}
    headers: dict[str, str] = {}
    auth: tuple[str, str] | None = None
    if token:
        headers["Authorization"] = f"GoogleLogin auth={token}"
    else:
        auth = (username, password)
    response = client.get(
        f"{api_base}/reader/api/0/stream/contents/reading-list",
        params=params,
        headers=headers,
        auth=auth,
    )
    response.raise_for_status()
    return response.json()


def run_fetch(
    config_path: Path,
    run_id: str,
    window_start: datetime,
    window_end: datetime,
    output_dir: Path,
    username: str,
    password: str,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    requested_sources = config.get("feed_ids") or ["ALL_SUBSCRIPTIONS"]
    api_base = normalize_api_base(config["base_url"])
    limit_per_run = int(config.get("limit_per_run", 100))
    timeout_seconds = int(config.get("request_timeout_seconds", 30))
    fetched_at = iso_now()
    source_config_hash = sha256_text(json.dumps(config, sort_keys=True))
    issues: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []
    raw_items: list[dict[str, Any]] = []
    try:
        with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
            payload = fetch_stream_response(client, api_base, username, password, limit_per_run)
        for item in payload.get("items", []):
            raw_item = build_raw_item(item, run_id, fetched_at)
            source_id = raw_item["source_id"]
            if config.get("feed_ids") and source_id not in config["feed_ids"]:
                continue
            published_at = raw_item.get("published_at")
            if published_at is None:
                continue
            published_dt = parse_iso8601(published_at)
            if window_start <= published_dt <= window_end:
                raw_items.append(raw_item)
        success_count = len(requested_sources)
        failure_count = 0
        partial_success = False
        for source in requested_sources:
            source_results.append({"source_id": source, "status": "SUCCESS", "error": None})
    except Exception as exc:  # noqa: BLE001
        success_count = 0
        failure_count = len(requested_sources)
        partial_success = False
        issues.append({"code": "FETCH_FAILED", "message": str(exc)})
        for source in requested_sources:
            source_results.append({"source_id": source, "status": "FAILED", "error": str(exc)})

    ensure_dir(output_dir)
    raw_items_path = output_dir / "raw-source-items.json"
    report_path = output_dir / "source-fetch-report.json"
    step_manifest_path = output_dir / "step-manifest.json"
    raw_items_payload = {
        "schema_name": "raw-source-items",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "item_count": len(raw_items),
        "items": raw_items,
    }
    report_payload = {
        "schema_name": "source-fetch-report",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": "FAILED" if success_count == 0 else ("PARTIAL_SUCCESS" if partial_success else "SUCCEEDED"),
        "continue_recommended": success_count > 0 and len(raw_items) > 0,
        "input_artifacts": [],
        "output_artifacts": [],
        "counts": {
            "requested_sources": len(requested_sources),
            "success_count": success_count,
            "failure_count": failure_count,
            "raw_item_count": len(raw_items)
        },
        "issues": issues,
        "payload": {
            "requested_sources": requested_sources,
            "success_count": success_count,
            "failure_count": failure_count,
            "partial_success": partial_success,
            "source_results": source_results,
            "source_config_hash": source_config_hash,
            "pipeline_version": PIPELINE_VERSION,
            "ruleset_version": RULESET_VERSION
        }
    }
    dump_json(raw_items_path, raw_items_payload)
    dump_json(report_path, report_payload)
    manifest_payload = {
        "schema_name": "step-manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_now(),
        "produced_by_skill": STEP_NAME,
        "run_id": run_id,
        "step_name": STEP_NAME,
        "step_status": report_payload["step_status"],
        "continue_recommended": success_count > 0 and len(raw_items) > 0,
        "input_artifacts": [],
        "output_artifacts": [
            {
                "artifact_name": "raw-source-items",
                "path": str(raw_items_path),
                "schema_name": "raw-source-items",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "PRIMARY",
                "consumable_by_downstream": len(raw_items) > 0,
                "required_for_next": True
            },
            {
                "artifact_name": "source-fetch-report",
                "path": str(report_path),
                "schema_name": "source-fetch-report",
                "schema_version": SCHEMA_VERSION,
                "artifact_role": "AUXILIARY",
                "consumable_by_downstream": True,
                "required_for_next": False
            }
        ],
        "counts": report_payload["counts"],
        "issues": issues,
        "payload": {
            "pipeline_version": PIPELINE_VERSION,
            "ruleset_version": RULESET_VERSION,
            "source_config_hash": source_config_hash
        }
    }
    dump_json(step_manifest_path, manifest_payload)
    return {"raw_items": raw_items_payload, "report": report_payload, "step_manifest": manifest_payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_fetch(
        config_path=Path(args.config),
        run_id=args.run_id,
        window_start=parse_iso8601(args.window_start),
        window_end=parse_iso8601(args.window_end),
        output_dir=Path(args.output_dir),
        username=os.environ["FRESHRSS_USERNAME"],
        password=os.environ["FRESHRSS_API_PASSWORD"]
    )


if __name__ == "__main__":
    main()
