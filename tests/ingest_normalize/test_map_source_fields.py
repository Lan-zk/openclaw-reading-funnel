import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_normalize.models import RawFeedItem, SourceDescriptor
import run


class MapSourceFieldsTests(unittest.TestCase):
    def test_invalid_item_fields_only_drop_current_item(self):
        descriptor = SourceDescriptor(
            source_id="rss-1",
            source_name="RSS One",
            adapter_type="RSS",
            enabled=True,
            fetch_policy={},
            endpoint="https://example.com/feed.xml",
        )
        items = [
            RawFeedItem(
                source_id="rss-1",
                origin_item_id="a1",
                title="Valid Title",
                url="https://example.com/posts/1",
                summary="ok",
                author="alice",
                published_at="2026-03-27T12:00:00+00:00",
                raw_payload={"id": "a1"},
            ),
            RawFeedItem(
                source_id="rss-1",
                origin_item_id="",
                title="Bad Title",
                url="https://example.com/posts/2",
                summary="bad",
                author="bob",
                published_at="2026-03-27T13:00:00+00:00",
                raw_payload={"id": "missing"},
            ),
        ]

        drafts, failures = run.map_source_fields(
            items,
            {"rss-1": descriptor},
            fetched_at="2026-03-27T14:00:00+00:00",
        )

        self.assertEqual(1, len(drafts))
        self.assertEqual("a1", drafts[0].origin_item_id)
        self.assertEqual(1, len(failures))
        self.assertEqual("MAPPING_ERROR", failures[0].failure_type)


if __name__ == "__main__":
    unittest.main()
