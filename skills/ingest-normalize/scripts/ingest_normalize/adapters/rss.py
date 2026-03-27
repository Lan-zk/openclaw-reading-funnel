"""RSS adapter."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .base import AdapterFailure, BaseAdapter, FetchRequest
from ..io_utils import ensure_utc_iso
from ..models import RawFeedItem, SourceDescriptor, SourceSyncPlan


class RSSAdapter(BaseAdapter):
    adapter_type = "RSS"

    def validate_source_config(self, source_config: dict[str, Any]) -> dict[str, Any]:
        endpoint = source_config.get("endpoint")
        if not endpoint:
            raise AdapterFailure(
                failure_type="CONFIG_ERROR",
                message="RSS source requires endpoint",
                details={"field": "endpoint"},
                retryable=False,
            )
        return dict(source_config)

    def build_fetch_request(self, descriptor: SourceDescriptor, plan: SourceSyncPlan) -> FetchRequest:
        timeout_seconds = int(descriptor.fetch_policy.get("request_timeout_seconds", 15))
        return FetchRequest(
            source_id=descriptor.source_id,
            adapter_type=descriptor.adapter_type,
            url=descriptor.endpoint or "",
            headers={"User-Agent": "ingest-normalize/0.1"},
            query={},
            timeout_seconds=timeout_seconds,
            plan_id=plan.plan_id,
            cursor=plan.cursor,
            mock_response=descriptor.adapter_config.get("mock_response"),
            mock_error=descriptor.adapter_config.get("mock_error"),
        )

    def fetch_batch(self, request: FetchRequest) -> Any:
        if request.mock_error:
            raise AdapterFailure(
                failure_type=request.mock_error.get("failure_type", "UNKNOWN_ERROR"),
                message=request.mock_error.get("message", "mock fetch failure"),
                details=request.mock_error,
                retryable=request.mock_error.get("failure_type") == "NETWORK_ERROR",
            )
        if request.mock_response is not None:
            return request.mock_response
        try:
            http_request = Request(url=request.url, headers=request.headers, method="GET")
            with urlopen(http_request, timeout=request.timeout_seconds) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise AdapterFailure("AUTH_ERROR", f"HTTP {exc.code}", {"status_code": exc.code}, False) from exc
            raise AdapterFailure("NETWORK_ERROR", f"HTTP {exc.code}", {"status_code": exc.code}, exc.code >= 500) from exc
        except URLError as exc:
            raise AdapterFailure("NETWORK_ERROR", str(exc.reason), {"url": request.url}, True) from exc

    def convert_response_to_feed_items(
        self,
        descriptor: SourceDescriptor,
        response: Any,
    ) -> tuple[list[RawFeedItem], dict[str, Any] | None]:
        try:
            root = ElementTree.fromstring(response)
        except ElementTree.ParseError as exc:
            raise AdapterFailure("PARSE_ERROR", str(exc), {"source_id": descriptor.source_id}, False) from exc

        items = self._rss_items(root)
        if items is None:
            items = self._atom_items(root)
        if items is None:
            raise AdapterFailure(
                "PARSE_ERROR",
                "Unsupported RSS/Atom structure",
                {"source_id": descriptor.source_id},
                False,
            )
        return items, None

    def _rss_items(self, root: ElementTree.Element) -> list[RawFeedItem] | None:
        channel = root.find("channel")
        if channel is None:
            return None
        items: list[RawFeedItem] = []
        for item in channel.findall("item"):
            link = _find_text(item, "link")
            guid = _find_text(item, "guid")
            title = _find_text(item, "title")
            item_id = guid or link or title
            if not item_id:
                continue
            items.append(
                RawFeedItem(
                    source_id="",
                    origin_item_id=item_id,
                    title=title,
                    url=link,
                    summary=_find_text(item, "description"),
                    author=_find_text(item, "author"),
                    published_at=_coerce_pubdate(_find_text(item, "pubDate")),
                    raw_payload={child.tag: (child.text or "") for child in list(item)},
                )
            )
        return items

    def _atom_items(self, root: ElementTree.Element) -> list[RawFeedItem] | None:
        if not root.tag.endswith("feed"):
            return None
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if not entries:
            return []
        items: list[RawFeedItem] = []
        for entry in entries:
            link = None
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = link_el.attrib.get("href")
            entry_id = _find_ns_text(entry, "atom:id", ns) or link or _find_ns_text(entry, "atom:title", ns)
            if not entry_id:
                continue
            items.append(
                RawFeedItem(
                    source_id="",
                    origin_item_id=entry_id,
                    title=_find_ns_text(entry, "atom:title", ns),
                    url=link,
                    summary=_find_ns_text(entry, "atom:summary", ns) or _find_ns_text(entry, "atom:content", ns),
                    author=_find_ns_text(entry, "atom:author/atom:name", ns),
                    published_at=ensure_utc_iso(_find_ns_text(entry, "atom:published", ns) or _find_ns_text(entry, "atom:updated", ns)),
                    raw_payload={child.tag: (child.text or "") for child in list(entry)},
                )
            )
        return items


def _find_text(node: ElementTree.Element, path: str) -> str | None:
    child = node.find(path)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _find_ns_text(node: ElementTree.Element, path: str, ns: dict[str, str]) -> str | None:
    child = node.find(path, ns)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _coerce_pubdate(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return ensure_utc_iso(value)
