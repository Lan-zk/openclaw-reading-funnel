"""GitHub feed adapter."""

from __future__ import annotations

from typing import Any

from .base import AdapterFailure
from .rss import RSSAdapter
from ..io_utils import ensure_utc_iso
from ..models import RawFeedItem, SourceDescriptor


class GitHubFeedAdapter(RSSAdapter):
    adapter_type = "GITHUB_FEED"

    def convert_response_to_feed_items(
        self,
        descriptor: SourceDescriptor,
        response: Any,
    ) -> tuple[list[RawFeedItem], dict[str, Any] | None]:
        if isinstance(response, dict):
            response = response.get("items", [])
        if isinstance(response, list):
            items: list[RawFeedItem] = []
            for item in response:
                item_id = str(item.get("id") or item.get("guid") or item.get("url") or "")
                if not item_id:
                    continue
                items.append(
                    RawFeedItem(
                        source_id=descriptor.source_id,
                        origin_item_id=item_id,
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
        if isinstance(response, str):
            return super().convert_response_to_feed_items(descriptor, response)
        raise AdapterFailure(
            "PARSE_ERROR",
            "GitHub feed response must be a list, dict, or RSS text",
            {"source_id": descriptor.source_id},
            False,
        )
