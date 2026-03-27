import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_normalize.models import SourceDescriptor
from tests.ingest_normalize.support import load_ingest_run_module


run = load_ingest_run_module("ingest_run_sync_window_tests")


class SyncSourceWindowTests(unittest.TestCase):
    def test_generates_incremental_plan_for_source(self):
        descriptor = SourceDescriptor(
            source_id="rss-1",
            source_name="RSS One",
            adapter_type="RSS",
            enabled=True,
            fetch_policy={"default_window_hours": 6, "page_limit": 1, "item_limit": 20},
            endpoint="https://example.com/feed.xml",
        )

        plans, failures = run.sync_source_window(
            [descriptor],
            runtime_overrides={"now": "2026-03-27T12:00:00+00:00"},
        )

        self.assertEqual(1, len(plans))
        self.assertEqual(0, len(failures))
        self.assertEqual("rss-1", plans[0].source_id)
        self.assertEqual("INCREMENTAL", plans[0].mode)
        self.assertEqual("2026-03-27T12:00:00+00:00", plans[0].until)

    def test_empty_window_returns_no_plan_without_failure(self):
        descriptor = SourceDescriptor(
            source_id="rss-1",
            source_name="RSS One",
            adapter_type="RSS",
            enabled=True,
            fetch_policy={"default_window_hours": 6},
            endpoint="https://example.com/feed.xml",
        )

        plans, failures = run.sync_source_window(
            [descriptor],
            runtime_overrides={
                "since": "2026-03-27T12:00:00+00:00",
                "until": "2026-03-27T12:00:00+00:00",
            },
        )

        self.assertEqual([], plans)
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
