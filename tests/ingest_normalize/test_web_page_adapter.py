import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_normalize.adapters import get_adapter
from ingest_normalize.adapters.base import AdapterFailure
from ingest_normalize.models import SourceDescriptor, SourceSyncPlan


class WebPageAdapterTests(unittest.TestCase):
    def test_build_fetch_request_uses_jina_reader_prefix_and_headers(self):
        adapter = get_adapter("WEB_PAGE")
        descriptor = SourceDescriptor(
            source_id="page-1",
            source_name="Example Page",
            adapter_type="WEB_PAGE",
            enabled=True,
            fetch_policy={"request_timeout_seconds": 15},
            endpoint="https://example.com/posts/1",
            adapter_config={
                "respond_with": "markdown",
                "target_selector": "article",
                "wait_for_selector": "article",
                "reader_timeout_seconds": 20,
                "no_cache": True,
            },
        )
        plan = SourceSyncPlan(
            source_id="page-1",
            plan_id="plan-1",
            mode="INCREMENTAL",
            since="2026-03-20T00:00:00+00:00",
            until="2026-03-27T00:00:00+00:00",
            cursor=None,
            page_limit=1,
            item_limit=1,
            planned_at="2026-03-27T00:00:00+00:00",
        )

        request = adapter.build_fetch_request(descriptor, plan)

        self.assertEqual("https://r.jina.ai/https://example.com/posts/1", request.url)
        self.assertEqual("application/json", request.headers["Accept"])
        self.assertEqual("markdown", request.headers["x-respond-with"])
        self.assertEqual("article", request.headers["x-target-selector"])
        self.assertEqual("article", request.headers["x-wait-for-selector"])
        self.assertEqual("20", request.headers["x-timeout"])
        self.assertEqual("true", request.headers["x-no-cache"])

    def test_convert_response_to_feed_items_maps_reader_json(self):
        adapter = get_adapter("WEB_PAGE")
        descriptor = SourceDescriptor(
            source_id="page-1",
            source_name="Example Page",
            adapter_type="WEB_PAGE",
            enabled=True,
            fetch_policy={},
            endpoint="https://example.com/posts/1",
            default_language="en",
        )

        items, cursor = adapter.convert_response_to_feed_items(
            descriptor,
            {
                "code": 200,
                "status": 20000,
                "data": {
                    "title": "Example Article",
                    "description": "Short summary",
                    "url": "https://example.com/posts/1",
                    "content": "# Example Article\n\nBody text",
                    "publishedTime": "Tue, 24 Mar 2026 22:06:31 GMT",
                    "metadata": {"lang": "en"},
                },
            },
        )

        self.assertIsNone(cursor)
        self.assertEqual(1, len(items))
        self.assertEqual("https://example.com/posts/1", items[0].origin_item_id)
        self.assertEqual("Example Article", items[0].title)
        self.assertEqual("Short summary", items[0].summary)
        self.assertEqual("2026-03-24T22:06:31+00:00", items[0].published_at)
        self.assertEqual("en", items[0].raw_payload["language"])
        self.assertEqual("# Example Article\n\nBody text", items[0].raw_payload["content"])

    def test_convert_response_to_feed_items_rejects_invalid_payload(self):
        adapter = get_adapter("WEB_PAGE")
        descriptor = SourceDescriptor(
            source_id="page-1",
            source_name="Example Page",
            adapter_type="WEB_PAGE",
            enabled=True,
            fetch_policy={},
            endpoint="https://example.com/posts/1",
        )

        with self.assertRaises(AdapterFailure) as ctx:
            adapter.convert_response_to_feed_items(descriptor, {"data": {}})

        self.assertEqual("PARSE_ERROR", ctx.exception.failure_type)


if __name__ == "__main__":
    unittest.main()
