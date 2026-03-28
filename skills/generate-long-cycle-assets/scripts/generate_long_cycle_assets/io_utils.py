"""I/O helpers for generate-long-cycle-assets."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def generate_run_id(now: datetime | None = None) -> str:
    current = now or utc_now()
    return current.strftime("run-%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]


def stable_hash(*parts: str) -> str:
    payload = "||".join(part.strip() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def slugify(text: str | None) -> str:
    if not text:
        return "untitled"
    chars: list[str] = []
    for char in text.lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-") or "untitled"


def titleize_token(token: str) -> str:
    return token.replace("-", " ").title()


def make_period_id(period_start: str, period_end: str) -> str:
    return f"pas_{stable_hash(period_start, period_end)[:20]}"


def make_topic_id(token: str) -> str:
    return f"topic_{slugify(token)}"


def make_signal_id(topic_id: str, signal_type: str) -> str:
    return f"ls_{stable_hash(topic_id, signal_type)[:20]}"


def make_asset_id(asset_scope: str, identity: str, run_id: str) -> str:
    prefix = "lca"
    return f"{prefix}_{stable_hash(asset_scope, identity, run_id)[:20]}"


def make_review_item_id(review_scope: str, related_object_id: str) -> str:
    return f"ari_{stable_hash(review_scope, related_object_id)[:20]}"


def make_failure_id(run_id: str, step_name: str, scope_type: str, scope_id: str | None, message: str) -> str:
    return f"lcf_{stable_hash(run_id, step_name, scope_type, scope_id or '', message)[:20]}"


def load_json_array(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        raw = json.load(handle)
    if isinstance(raw, list):
        return raw
    raise ValueError(f"expected JSON array in {source}")


def prepare_output_directory(output_root: str | Path, run_id: str) -> Path:
    run_dir = Path(output_root) / "generate-long-cycle-assets" / run_id
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


def write_text(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
