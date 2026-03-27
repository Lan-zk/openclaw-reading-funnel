"""I/O helpers for compose-daily-review."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import DigestCandidate


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


def parse_iso_datetime(value: str | None) -> datetime | None:
    normalized = ensure_utc_iso(value)
    if normalized is None:
        return None
    return datetime.fromisoformat(normalized)


def resolve_issue_date(issue_date: str | None) -> str:
    if issue_date:
        return date.fromisoformat(issue_date).isoformat()
    return utc_now().date().isoformat()


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


def make_failure_id(run_id: str, step_name: str, scope_type: str, scope_id: str | None, message: str) -> str:
    return f"crf_{stable_hash(run_id, step_name, scope_type, scope_id or '', message)[:20]}"


def make_event_bundle_id(group_key: str) -> str:
    return f"bundle_{stable_hash(group_key)[:20]}"


def make_theme_id(label: str) -> str:
    return f"theme_{stable_hash(label)[:20]}"


def make_review_item_id(event_bundle_id: str) -> str:
    return f"eri_{stable_hash(event_bundle_id)[:20]}"


def make_entry_id(event_bundle_id: str, section: str) -> str:
    return f"dre_{stable_hash(event_bundle_id, section)[:20]}"


def make_issue_id(issue_date: str, run_id: str) -> str:
    return f"dri_{stable_hash(issue_date, run_id)[:20]}"


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
    query_pairs = []
    for key, raw_value in parse_qsl(split.query, keep_blank_values=True):
        if key.lower().startswith("utm_"):
            continue
        query_pairs.append((key, raw_value))
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, split.path or "", query, ""))


def load_digest_candidates(path: str | Path) -> list[DigestCandidate]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        raw_items = json.load(handle)
    return [
        DigestCandidate(
            digest_candidate_id=item["digest_candidate_id"],
            normalized_candidate_ids=list(item["normalized_candidate_ids"]),
            primary_normalized_candidate_id=item["primary_normalized_candidate_id"],
            cluster_type=item["cluster_type"],
            cluster_confidence=float(item["cluster_confidence"]),
            display_title=item["display_title"],
            display_summary=item.get("display_summary"),
            canonical_url=item.get("canonical_url"),
            quality_score=_as_float(item.get("quality_score")),
            freshness_score=_as_float(item.get("freshness_score")),
            digest_score=_as_float(item.get("digest_score")),
            noise_flags=list(item.get("noise_flags", [])),
            needs_review=bool(item["needs_review"]),
            digest_status=item["digest_status"],
            run_id=item["run_id"],
        )
        for item in raw_items
    ]


def load_preference_signals(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def prepare_output_directory(output_root: str | Path, run_id: str) -> Path:
    run_dir = Path(output_root) / "compose-daily-review" / run_id
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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
