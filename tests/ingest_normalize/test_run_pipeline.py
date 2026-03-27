import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from ingest_normalize import pipeline as pipeline_module
from tests.ingest_normalize.support import load_ingest_run_module, workspace_tempdir


run = load_ingest_run_module("ingest_run_pipeline_tests")


class RunPipelineTests(unittest.TestCase):
    def test_minimal_happy_path_writes_required_artifacts(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
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
                                "mock_response": """<?xml version='1.0'?>
<rss version='2.0'><channel><title>demo</title>
<item><guid>a1</guid><title>Hello</title><link>https://example.com/posts/1</link><description>World</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
</channel></rss>""",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="run-happy",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )

            run_dir = output_root / "ingest-normalize" / "run-happy"
            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertTrue((run_dir / "source-entries.json").exists())
            self.assertTrue((run_dir / "normalized-candidates.json").exists())
            self.assertTrue((run_dir / "ingest-failures.json").exists())
            self.assertTrue((run_dir / "step-manifest.json").exists())
            self.assertTrue((run_dir / "ingest-report.json").exists())

    def test_web_page_jina_reader_happy_path(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
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
                                "mock_response": {
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
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="run-web-page",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )

            run_dir = output_root / "ingest-normalize" / "run-web-page"
            entries = json.loads((run_dir / "source-entries.json").read_text(encoding="utf-8"))
            candidates = json.loads((run_dir / "normalized-candidates.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, result["source_entry_count"])
            self.assertEqual(1, result["normalized_candidate_count"])
            self.assertEqual("https://example.com/posts/1", entries[0]["origin_item_id"])
            self.assertEqual("https://example.com/posts/1", entries[0]["url"])
            self.assertEqual("https://example.com/posts/1", candidates[0]["canonical_url"])

    def test_single_source_timeout_records_network_error(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
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
                                "mock_error": {"failure_type": "NETWORK_ERROR", "message": "timeout"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="run-timeout",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )

            self.assertEqual("PARTIAL_SUCCESS", result["workflow_status"])
            failures = json.loads(
                (output_root / "ingest-normalize" / "run-timeout" / "ingest-failures.json").read_text(encoding="utf-8")
            )
            self.assertEqual("NETWORK_ERROR", failures[0]["failure_type"])

    def test_convert_failure_records_parse_error(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
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
                                "mock_response": "<rss><broken>",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="run-parse",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )

            self.assertEqual("PARTIAL_SUCCESS", result["workflow_status"])
            failures = json.loads(
                (output_root / "ingest-normalize" / "run-parse" / "ingest-failures.json").read_text(encoding="utf-8")
            )
            self.assertEqual("PARSE_ERROR", failures[0]["failure_type"])

    def test_source_entry_is_only_created_after_successful_persist(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
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
                                "mock_response": """<?xml version='1.0'?>
<rss version='2.0'><channel><title>demo</title>
<item><guid>a1</guid><title>Hello</title><link>https://example.com/posts/1</link></item>
</channel></rss>""",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(pipeline_module, "persist_source_entries", side_effect=OSError("disk full")):
                result = run.run_pipeline(
                    source_config_path=str(config_path),
                    output_root=str(output_root),
                    run_id="run-persist-fail",
                    runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
                )

            self.assertEqual("FAILED", result["workflow_status"])
            entries = json.loads(
                (output_root / "ingest-normalize" / "run-persist-fail" / "source-entries.json").read_text(encoding="utf-8")
            )
            self.assertEqual([], entries)

    def test_step_manifest_reflects_step_statuses(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
            config_path.write_text(json.dumps({"sources": []}), encoding="utf-8")

            run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="run-empty",
                runtime_overrides={},
            )

            manifest = json.loads(
                (output_root / "ingest-normalize" / "run-empty" / "step-manifest.json").read_text(encoding="utf-8")
            )

            statuses = {item["step_name"]: item["status"] for item in manifest["step_results"]}
            self.assertEqual("SUCCESS_EMPTY", statuses["discover_sources"])
            self.assertEqual("SUCCESS_EMPTY", statuses["normalize_candidates"])

    def test_output_directory_not_writable_marks_workflow_failed(self):
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            output_root = tmp / "artifacts"
            config_path.write_text(json.dumps({"sources": []}), encoding="utf-8")

            with mock.patch.object(pipeline_module, "prepare_output_directory", side_effect=PermissionError("denied")):
                result = run.run_pipeline(
                    source_config_path=str(config_path),
                    output_root=str(output_root),
                    run_id="run-denied",
                    runtime_overrides={},
                )

            self.assertEqual("FAILED", result["workflow_status"])


if __name__ == "__main__":
    unittest.main()
