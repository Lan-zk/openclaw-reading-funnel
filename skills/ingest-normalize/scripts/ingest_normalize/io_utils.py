"""I/O helpers for ingest-normalize."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRACKING_PARAM_PATTERN = re.compile(r"^utm_")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def ensure_utc_iso(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def generate_run_id(now: datetime | None = None) -> str:
    current = now or utc_now()
    return current.strftime("run-%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]


def stable_hash(*parts: str) -> str:
    payload = "||".join(part.strip() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_source_entry_id(source_id: str, origin_item_id: str) -> str:
    return f"se_{stable_hash(source_id, origin_item_id)[:20]}"


def make_source_entry_snapshot_id(source_entry_id: str, fetched_at: str | None = None) -> str:
    snapshot_time = (fetched_at or iso_now()).replace(":", "").replace("-", "")
    return f"ses_{snapshot_time}_{stable_hash(source_entry_id, fetched_at or '')[:12]}"


def make_normalized_candidate_id(source_entry_id: str) -> str:
    return f"nc_{stable_hash(source_entry_id)[:20]}"


def make_failure_id(run_id: str, step_name: str, scope_type: str, scope_id: str | None, message: str) -> str:
    return f"if_{stable_hash(run_id, step_name, scope_type, scope_id or '', message)[:20]}"


def make_plan_id(source_id: str, since: str | None, until: str) -> str:
    return f"plan_{stable_hash(source_id, since or '', until)[:20]}"


def make_url_fingerprint(canonical_url: str | None) -> str | None:
    if not canonical_url:
        return None
    return stable_hash(canonical_url)[:24]


def load_source_config(source_config_path: str | Path) -> dict[str, Any]:
    path = Path(source_config_path)
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def prepare_output_directory(output_root: str | Path, run_id: str) -> Path:
    run_dir = Path(output_root) / "ingest-normalize" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _jsonable(data: Any) -> Any:
    if isinstance(data, Path):
        return str(data)
    if hasattr(data, "to_dict"):
        return data.to_dict()
    if is_dataclass(data):
        return data
    if isinstance(data, list):
        return [_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: _jsonable(item) for key, item in data.items()}
    return data


def write_json(path: str | Path, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(_jsonable(data), handle, ensure_ascii=False, indent=2)
    return target
