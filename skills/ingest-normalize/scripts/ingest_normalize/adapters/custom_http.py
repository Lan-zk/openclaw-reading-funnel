"""Custom HTTP adapter."""

from __future__ import annotations

import json
from typing import Any

from .base import AdapterFailure
from .rss import RSSAdapter
from ..io_utils import ensure_utc_iso
from ..models import RawFeedItem, SourceDescriptor


class CustomHTTPAdapter(RSSAdapter):
    adapter_type = "CUSTOM_HTTP"

    def convert_response_to_feed_items(
        self,
        descriptor: SourceDescriptor,
        response: Any,
    ) -> tuple[list[RawFeedItem], dict[str, Any] | None]:
        payload = response
        if isinstance(response, str):
            stripped = response.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                payload = json.loads(stripped)
            else:
                return super().convert_response_to_feed_items(descriptor, response)
        if isinstance(payload, dict):
            payload = payload.get("items", [])
        if not isinstance(payload, list):
            raise AdapterFailure(
                "PARSE_ERROR",
                "Custom HTTP response must be a list, dict, JSON text, or RSS text",
                {"source_id": descriptor.source_id},
                False,
            )
        items: list[RawFeedItem] = []
        for item in payload:
            origin_item_id = str(item.get("origin_item_id") or item.get("id") or item.get("url") or "")
            if not origin_item_id:
                continue
            items.append(
                RawFeedItem(
                    source_id=descriptor.source_id,
                    origin_item_id=origin_item_id,
                    title=item.get("title"),
                    url=item.get("url"),
                    summary=item.get("summary"),
                    author=item.get("author"),
                    published_at=ensure_utc_iso(item.get("published_at")),
                    raw_payload=dict(item),
                    language=item.get("language"),
                )
            )
        return items, None
