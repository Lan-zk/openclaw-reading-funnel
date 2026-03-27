import json
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import run
from support import workspace_tempdir


class DiscoverSourcesTests(unittest.TestCase):
    def test_valid_config_creates_source_descriptor(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_id": "rss-1",
                                "source_name": "RSS One",
                                "adapter_type": "RSS",
                                "enabled": True,
                                "endpoint": "https://example.com/feed.xml",
                                "fetch_policy": {"default_window_hours": 24},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            descriptors, failures = run.discover_sources(str(config_path), {})

            self.assertEqual(1, len(descriptors))
            self.assertEqual(0, len(failures))
            self.assertEqual("rss-1", descriptors[0].source_id)
            self.assertEqual("RSS", descriptors[0].adapter_type)

    def test_web_page_config_keeps_reader_settings(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_id": "page-1",
                                "source_name": "Example Page",
                                "adapter_type": "WEB_PAGE",
                                "enabled": True,
                                "endpoint": "https://example.com/posts/1",
                                "fetch_policy": {"default_window_hours": 168},
                                "respond_with": "markdown",
                                "target_selector": "article",
                                "wait_for_selector": "article",
                                "reader_timeout_seconds": 20,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            descriptors, failures = run.discover_sources(str(config_path), {})

            self.assertEqual(1, len(descriptors))
            self.assertEqual([], failures)
            self.assertEqual("WEB_PAGE", descriptors[0].adapter_type)
            self.assertEqual("markdown", descriptors[0].adapter_config["respond_with"])
            self.assertEqual("article", descriptors[0].adapter_config["target_selector"])
            self.assertEqual(20, descriptors[0].adapter_config["reader_timeout_seconds"])

    def test_invalid_source_config_is_recorded_without_blocking_others(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_id": "bad-rss",
                                "source_name": "Bad RSS",
                                "adapter_type": "RSS",
                                "enabled": True,
                                "fetch_policy": {"default_window_hours": 24},
                            },
                            {
                                "source_id": "good-rss",
                                "source_name": "Good RSS",
                                "adapter_type": "RSS",
                                "enabled": True,
                                "endpoint": "https://example.com/feed.xml",
                                "fetch_policy": {"default_window_hours": 24},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            descriptors, failures = run.discover_sources(str(config_path), {})

            self.assertEqual(["good-rss"], [item.source_id for item in descriptors])
            self.assertEqual(1, len(failures))
            self.assertEqual("discover_sources", failures[0].step_name)
            self.assertEqual("CONFIG_ERROR", failures[0].failure_type)


if __name__ == "__main__":
    unittest.main()
