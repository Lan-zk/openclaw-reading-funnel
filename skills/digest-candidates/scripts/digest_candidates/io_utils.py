"""I/O helpers for digest-candidates."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import NormalizedCandidate


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"spm", "from"}


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
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    normalized = ensure_utc_iso(value)
    if normalized is None:
        return None
    return datetime.fromisoformat(normalized)


def generate_run_id(now: datetime | None = None) -> str:
    current = now or utc_now()
    return current.strftime("run-%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]


def stable_hash(*parts: str) -> str:
    payload = "||".join(part.strip() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_failure_id(run_id: str, step_name: str, scope_type: str, scope_id: str | None, message: str) -> str:
    return f"df_{stable_hash(run_id, step_name, scope_type, scope_id or '', message)[:20]}"


def make_cluster_id(member_candidate_ids: list[str]) -> str:
    material = "|".join(sorted(member_candidate_ids))
    return f"cluster_{stable_hash(material)[:20]}"


def make_digest_candidate_id(cluster_id: str) -> str:
    return f"dc_{stable_hash(cluster_id)[:20]}"


def make_review_item_id(cluster_id: str) -> str:
    return f"dri_{stable_hash(cluster_id)[:20]}"


def make_url_fingerprint(canonical_url: str | None) -> str | None:
    if not canonical_url:
        return None
    return stable_hash(canonical_url)[:24]


def normalize_url(url: str | None) -> str | None:
    if url is None:
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
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    query_pairs = []
    for key, raw_value in parse_qsl(split.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith(TRACKING_PREFIXES) or lowered in TRACKING_KEYS:
            continue
        query_pairs.append((key, raw_value))
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, split.path or "", query, ""))


def load_normalized_candidates(path: str | Path) -> list[NormalizedCandidate]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as handle:
        raw_items = json.load(handle)
    return [
        NormalizedCandidate(
            normalized_candidate_id=item["normalized_candidate_id"],
            source_entry_id=item["source_entry_id"],
            canonical_url=item.get("canonical_url"),
            url_fingerprint=item.get("url_fingerprint"),
            title=item.get("title"),
            normalized_title=item.get("normalized_title"),
            summary=item.get("summary"),
            language=item.get("language"),
            published_at=item.get("published_at"),
            source_id=item["source_id"],
            source_name=item["source_name"],
            normalize_status=item["normalize_status"],
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
    run_dir = Path(output_root) / "digest-candidates" / run_id
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
