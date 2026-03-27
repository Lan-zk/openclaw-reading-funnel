"""Adapter registry for ingest-normalize."""

from .custom_http import CustomHTTPAdapter
from .github_feed import GitHubFeedAdapter
from .rss import RSSAdapter
from .rsshub import RSSHubAdapter
from .web_page import WebPageAdapter


ADAPTER_REGISTRY = {
    "RSS": RSSAdapter(),
    "RSSHUB": RSSHubAdapter(),
    "GITHUB_FEED": GitHubFeedAdapter(),
    "CUSTOM_HTTP": CustomHTTPAdapter(),
    "WEB_PAGE": WebPageAdapter(),
}


def get_adapter(adapter_type: str):
    try:
        return ADAPTER_REGISTRY[adapter_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported adapter_type: {adapter_type}") from exc
