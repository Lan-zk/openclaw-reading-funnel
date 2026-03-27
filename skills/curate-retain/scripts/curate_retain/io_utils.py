"""I/O helpers for curate-retain."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


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


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    split = urlsplit(value)
    scheme = (split.scheme or "https").lower()
    netloc = split.netloc.lower()
    if not netloc and split.path:
        split = urlsplit(f"https://{value}")
        scheme = split.scheme.lower()
        netloc = split.netloc.lower()
    return urlunsplit((scheme, netloc, split.path or "", split.query, ""))


def extract_source_name(url: str | None) -> str | None:
    normalized = normalize_url(url)
    if not normalized:
        return None
    return urlsplit(normalized).netloc or None


def add_days(iso_value: str | None, days: int) -> str:
    if iso_value:
        normalized = iso_value.replace("Z", "+00:00")
        base = datetime.fromisoformat(normalized)
    else:
        base = utc_now()
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return (base.astimezone(timezone.utc) + timedelta(days=days)).isoformat()


def make_failure_id(run_id: str, step_name: str, scope_type: str, scope_id: str | None, message: str) -> str:
    return f"crf_{stable_hash(run_id, step_name, scope_type, scope_id or '', message)[:20]}"


def make_queue_item_id(target_type: str, target_id: str) -> str:
    return f"rqi_{stable_hash(target_type, target_id)[:20]}"


def make_retention_decision_id(target_type: str, target_id: str, decision_at: str, decision_by: str) -> str:
    return f"rdr_{stable_hash(target_type, target_id, decision_at, decision_by)[:20]}"


def make_knowledge_asset_id(origin_retention_decision_id: str, title: str | None) -> str:
    return f"ka_{stable_hash(origin_retention_decision_id, title or '')[:20]}"


def make_preference_signal_id(signal_type: str, signal_value: str, origin_retention_decision_id: str) -> str:
    return f"ps_{stable_hash(signal_type, signal_value, origin_retention_decision_id)[:20]}"


def load_json_array(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        raw = json.load(handle)
    if isinstance(raw, list):
        return raw
    raise ValueError(f"expected JSON array in {source}")


def load_daily_review_issues(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return load_json_array(path)


def load_human_decisions(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return load_json_array(path)


def prepare_output_directory(output_root: str | Path, run_id: str) -> Path:
    run_dir = Path(output_root) / "curate-retain" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: str | Path, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return target


def write_text(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
