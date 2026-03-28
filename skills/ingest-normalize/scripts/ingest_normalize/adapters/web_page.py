"""Generic web page adapter backed by Jina Reader."""

from __future__ import annotations

import json
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .base import AdapterFailure, BaseAdapter, FetchRequest
from ..io_utils import ensure_utc_iso
from ..models import RawFeedItem, SourceDescriptor, SourceSyncPlan


class WebPageAdapter(BaseAdapter):
    adapter_type = "WEB_PAGE"
    reader_base_url = "https://r.jina.ai/"

    def validate_source_config(self, source_config: dict[str, Any]) -> dict[str, Any]:
        endpoint = (source_config.get("endpoint") or "").strip()
        if not endpoint:
            raise AdapterFailure(
                failure_type="CONFIG_ERROR",
                message="WEB_PAGE source requires endpoint",
                details={"field": "endpoint"},
                retryable=False,
            )
        parts = urlsplit(endpoint)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise AdapterFailure(
                failure_type="CONFIG_ERROR",
                message="WEB_PAGE endpoint must be an absolute http(s) URL",
                details={"field": "endpoint", "value": endpoint},
                retryable=False,
            )
        normalized = dict(source_config)
        normalized.setdefault("respond_with", "markdown")
        return normalized

    def build_fetch_request(self, descriptor: SourceDescriptor, plan: SourceSyncPlan) -> FetchRequest:
        timeout_seconds = int(descriptor.fetch_policy.get("request_timeout_seconds", 20))
        headers = {
            "User-Agent": "ingest-normalize/0.1",
            "Accept": "application/json",
        }
        respond_with = descriptor.adapter_config.get("respond_with")
        target_selector = descriptor.adapter_config.get("target_selector")
        wait_for_selector = descriptor.adapter_config.get("wait_for_selector")
        reader_timeout_seconds = descriptor.adapter_config.get("reader_timeout_seconds")
        if respond_with:
            headers["x-respond-with"] = str(respond_with)
        if target_selector:
            headers["x-target-selector"] = str(target_selector)
        if wait_for_selector:
            headers["x-wait-for-selector"] = str(wait_for_selector)
        if reader_timeout_seconds is not None:
            headers["x-timeout"] = str(reader_timeout_seconds)
        if descriptor.adapter_config.get("no_cache"):
            headers["x-no-cache"] = "true"
        if descriptor.adapter_config.get("with_generated_alt"):
            headers["x-with-generated-alt"] = "true"
        return FetchRequest(
            source_id=descriptor.source_id,
            adapter_type=descriptor.adapter_type,
            url=self._reader_url(descriptor.endpoint or ""),
            headers=headers,
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
        payload = response
        if isinstance(response, str):
            try:
                payload = json.loads(response)
            except json.JSONDecodeError as exc:
                raise AdapterFailure(
                    "PARSE_ERROR",
                    "WEB_PAGE response must be JSON from Jina Reader",
                    {"source_id": descriptor.source_id},
                    False,
                ) from exc
        if not isinstance(payload, dict):
            raise AdapterFailure(
                "PARSE_ERROR",
                "WEB_PAGE response must be a JSON object",
                {"source_id": descriptor.source_id},
                False,
            )
        data = payload.get("data", payload)
        if not isinstance(data, dict):
            raise AdapterFailure(
                "PARSE_ERROR",
                "WEB_PAGE response data must be an object",
                {"source_id": descriptor.source_id},
                False,
            )

        page_url = str(data.get("url") or descriptor.endpoint or "").strip()
        title = _optional_text(data.get("title"))
        content = _optional_text(data.get("content"))
        description = _optional_text(data.get("description"))
        if not any((data.get("url"), title, content, description)):
            raise AdapterFailure(
                "PARSE_ERROR",
                "WEB_PAGE response does not contain any extracted page fields",
                {"source_id": descriptor.source_id},
                False,
            )
        if not page_url and not title:
            raise AdapterFailure(
                "PARSE_ERROR",
                "WEB_PAGE response requires at least one of url or title",
                {"source_id": descriptor.source_id},
                False,
            )

        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        language = (
            _optional_text(data.get("language"))
            or _optional_text(metadata.get("lang"))
            or descriptor.default_language
        )
        raw_payload = dict(data)
        raw_payload["language"] = language
        if content is not None:
            raw_payload["content"] = content

        item = RawFeedItem(
            source_id=descriptor.source_id,
            origin_item_id=page_url or title or descriptor.source_id,
            title=title,
            url=page_url or None,
            summary=description or _excerpt(content),
            author=_optional_text(data.get("author")),
            published_at=_coerce_published_at(data.get("publishedTime") or data.get("published_at")),
            raw_payload=raw_payload,
            language=language,
        )
        return [item], None

    def _reader_url(self, endpoint: str) -> str:
        if endpoint.startswith(self.reader_base_url):
            return endpoint
        return f"{self.reader_base_url}{endpoint}"


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _excerpt(content: str | None, limit: int = 280) -> str | None:
    if not content:
        return None
    flattened = " ".join(part for part in content.splitlines() if part.strip())
    if len(flattened) <= limit:
        return flattened
    return flattened[: limit - 1].rstrip() + "…"


def _coerce_published_at(value: Any) -> str | None:
    text = _optional_text(value)
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).isoformat()
    except (TypeError, ValueError, IndexError):
        return ensure_utc_iso(text)
