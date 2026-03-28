import json
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "digest-candidates"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

INGEST_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(INGEST_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(INGEST_SKILL_DIR))
INGEST_SCRIPT_DIR = INGEST_SKILL_DIR / "scripts"
if str(INGEST_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(INGEST_SCRIPT_DIR))

import importlib.util
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from support import workspace_tempdir


def load_digest_run_module():
    module_path = SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("digest_run_for_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_ingest_run_module():
    module_path = INGEST_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("ingest_run_for_digest_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunPipelineTests(unittest.TestCase):
    def test_empty_input_produces_success_with_empty_artifacts(self):
        digest_run = load_digest_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "normalized-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text("[]", encoding="utf-8")

            result = digest_run.run_pipeline(
                normalized_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="digest-run-empty",
            )

            run_dir = output_root / "digest-candidates" / "digest-run-empty"
            candidates = json.loads((run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual([], candidates)
            self.assertEqual("SUCCESS_EMPTY", manifest["step_results"][-1]["status"])

    def test_minimal_happy_path_writes_required_artifacts(self):
        digest_run = load_digest_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "normalized-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "normalized_candidate_id": "nc-1",
                            "source_entry_id": "se-1",
                            "canonical_url": "https://example.com/post-1?utm_source=x",
                            "url_fingerprint": "fp-source",
                            "title": "Example post",
                            "normalized_title": "Example post",
                            "summary": "A concise summary.",
                            "language": "en",
                            "published_at": "2026-03-27T12:00:00+00:00",
                            "source_id": "rss-1",
                            "source_name": "RSS One",
                            "normalize_status": "NORMALIZED",
                            "run_id": "ingest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = digest_run.run_pipeline(
                normalized_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="digest-run-happy",
            )

            run_dir = output_root / "digest-candidates" / "digest-run-happy"
            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertTrue((run_dir / "digest-candidates.json").exists())
            self.assertTrue((run_dir / "digest-review.json").exists())
            self.assertTrue((run_dir / "digest-failures.json").exists())
            self.assertTrue((run_dir / "step-manifest.json").exists())
            self.assertTrue((run_dir / "digest-report.md").exists())

            candidates = json.loads((run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(candidates))
            self.assertEqual("KEPT", candidates[0]["digest_status"])
            self.assertEqual("https://example.com/post-1", candidates[0]["canonical_url"])

    def test_low_signal_candidate_enters_review_pool(self):
        digest_run = load_digest_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "normalized-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "normalized_candidate_id": "nc-low",
                            "source_entry_id": "se-low",
                            "canonical_url": "https://example.com/post-low",
                            "url_fingerprint": "fp-low",
                            "title": "Low signal",
                            "normalized_title": "Low signal",
                            "summary": None,
                            "language": "en",
                            "published_at": None,
                            "source_id": "rss-1",
                            "source_name": "RSS One",
                            "normalize_status": "NORMALIZED",
                            "run_id": "ingest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = digest_run.run_pipeline(
                normalized_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="digest-run-review",
            )

            run_dir = output_root / "digest-candidates" / "digest-run-review"
            candidates = json.loads((run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "digest-review.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(candidates))
            self.assertEqual("NEEDS_REVIEW", candidates[0]["digest_status"])
            self.assertEqual(1, len(review_items))

    def test_exact_duplicates_are_folded_into_one_digest_candidate(self):
        digest_run = load_digest_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "normalized-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "normalized_candidate_id": "nc-1",
                            "source_entry_id": "se-1",
                            "canonical_url": "https://example.com/post-1?utm_source=x",
                            "url_fingerprint": "dup-fingerprint",
                            "title": "Example post",
                            "normalized_title": "Example post",
                            "summary": "Same summary",
                            "language": "en",
                            "published_at": "2026-03-27T12:00:00+00:00",
                            "source_id": "rss-1",
                            "source_name": "RSS One",
                            "normalize_status": "NORMALIZED",
                            "run_id": "ingest-run",
                        },
                        {
                            "normalized_candidate_id": "nc-2",
                            "source_entry_id": "se-2",
                            "canonical_url": "https://example.com/post-1?utm_medium=rss",
                            "url_fingerprint": "dup-fingerprint",
                            "title": "Example post repost",
                            "normalized_title": "Example post repost",
                            "summary": "Same summary",
                            "language": "en",
                            "published_at": "2026-03-27T12:05:00+00:00",
                            "source_id": "rss-2",
                            "source_name": "RSS Two",
                            "normalize_status": "NORMALIZED",
                            "run_id": "ingest-run",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            result = digest_run.run_pipeline(
                normalized_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="digest-run-dedup",
            )

            run_dir = output_root / "digest-candidates" / "digest-run-dedup"
            candidates = json.loads((run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(candidates))
            self.assertEqual(2, len(candidates[0]["normalized_candidate_ids"]))

    def test_ingest_then_digest_integration_produces_digest_candidate(self):
        ingest_run = load_ingest_run_module()
        digest_run = load_digest_run_module()
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
<item><guid>a1</guid><title>Hello Digest</title><link>https://example.com/posts/1?utm_source=x</link><description>World</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
</channel></rss>""",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            ingest_result = ingest_run.run_pipeline(
                source_config_path=str(config_path),
                output_root=str(output_root),
                run_id="ingest-run",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )
            self.assertEqual("SUCCEEDED", ingest_result["workflow_status"])

            digest_result = digest_run.run_pipeline(
                normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
                output_root=str(output_root),
                run_id="digest-from-ingest",
            )

            run_dir = output_root / "digest-candidates" / "digest-from-ingest"
            candidates = json.loads((run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", digest_result["workflow_status"])
            self.assertEqual(1, len(candidates))
            self.assertEqual("KEPT", candidates[0]["digest_status"])
            self.assertEqual("digest-candidates", manifest["workflow_name"])

    def test_missing_input_file_marks_workflow_failed(self):
        digest_run = load_digest_run_module()
        with workspace_tempdir() as tmp:
            output_root = tmp / "artifacts"

            result = digest_run.run_pipeline(
                normalized_candidates_path=str(tmp / "missing.json"),
                output_root=str(output_root),
                run_id="digest-run-missing",
            )

            self.assertEqual("FAILED", result["workflow_status"])


if __name__ == "__main__":
    unittest.main()
