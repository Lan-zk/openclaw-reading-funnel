import importlib.util
import json
import sys
import unittest
from pathlib import Path


COMPOSE_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "compose-daily-review"
if str(COMPOSE_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(COMPOSE_SKILL_DIR))
COMPOSE_SCRIPT_DIR = COMPOSE_SKILL_DIR / "scripts"
if str(COMPOSE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(COMPOSE_SCRIPT_DIR))

DIGEST_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "digest-candidates"
if str(DIGEST_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(DIGEST_SKILL_DIR))
DIGEST_SCRIPT_DIR = DIGEST_SKILL_DIR / "scripts"
if str(DIGEST_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(DIGEST_SCRIPT_DIR))

INGEST_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(INGEST_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(INGEST_SKILL_DIR))
INGEST_SCRIPT_DIR = INGEST_SKILL_DIR / "scripts"
if str(INGEST_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(INGEST_SCRIPT_DIR))

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from support import workspace_tempdir


def load_compose_run_module():
    module_path = COMPOSE_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("compose_run_for_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_digest_run_module():
    module_path = DIGEST_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("digest_run_for_compose_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_ingest_run_module():
    module_path = INGEST_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("ingest_run_for_compose_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunPipelineTests(unittest.TestCase):
    def test_empty_input_produces_success_with_empty_artifacts(self):
        compose_run = load_compose_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "digest-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text("[]", encoding="utf-8")

            result = compose_run.run_pipeline(
                digest_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="compose-run-empty",
                issue_date="2026-03-27",
            )

            run_dir = output_root / "compose-daily-review" / "compose-run-empty"
            issues = json.loads((run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "editorial-review.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual([], issues)
            self.assertEqual([], review_items)
            self.assertEqual("SUCCESS_EMPTY", manifest["step_results"][-2]["status"])
            self.assertEqual("SUCCESS_EMPTY", manifest["step_results"][-1]["status"])

    def test_minimal_happy_path_writes_required_artifacts(self):
        compose_run = load_compose_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "digest-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "digest_candidate_id": "dc-1",
                            "normalized_candidate_ids": ["nc-1"],
                            "primary_normalized_candidate_id": "nc-1",
                            "cluster_type": "SINGLE",
                            "cluster_confidence": 0.98,
                            "display_title": "Python 3.13 security release",
                            "display_summary": "Security fixes and release notes for the Python ecosystem.",
                            "canonical_url": "https://example.com/python-313-security",
                            "quality_score": 0.94,
                            "freshness_score": 0.90,
                            "digest_score": 0.93,
                            "noise_flags": [],
                            "needs_review": False,
                            "digest_status": "KEPT",
                            "run_id": "digest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = compose_run.run_pipeline(
                digest_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="compose-run-happy",
                issue_date="2026-03-27",
            )

            run_dir = output_root / "compose-daily-review" / "compose-run-happy"
            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertTrue((run_dir / "daily-review-issues.json").exists())
            self.assertTrue((run_dir / "editorial-review.json").exists())
            self.assertTrue((run_dir / "daily-review-failures.json").exists())
            self.assertTrue((run_dir / "step-manifest.json").exists())
            self.assertTrue((run_dir / "daily-review-report.md").exists())
            self.assertTrue((run_dir / "daily-review.md").exists())

            issues = json.loads((run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            self.assertEqual(1, len(issues))
            self.assertEqual("COMPOSED", issues[0]["render_status"])
            self.assertEqual("2026-03-27", issues[0]["issue_date"])
            self.assertGreaterEqual(sum(len(entries) for entries in issues[0]["sections"].values()), 1)

    def test_low_confidence_candidate_enters_editor_review(self):
        compose_run = load_compose_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "digest-candidates.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "digest_candidate_id": "dc-review",
                            "normalized_candidate_ids": ["nc-review"],
                            "primary_normalized_candidate_id": "nc-review",
                            "cluster_type": "SINGLE",
                            "cluster_confidence": 0.51,
                            "display_title": "A vague platform update",
                            "display_summary": None,
                            "canonical_url": None,
                            "quality_score": 0.42,
                            "freshness_score": 0.60,
                            "digest_score": 0.55,
                            "noise_flags": [],
                            "needs_review": True,
                            "digest_status": "NEEDS_REVIEW",
                            "run_id": "digest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = compose_run.run_pipeline(
                digest_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="compose-run-review",
                issue_date="2026-03-27",
            )

            run_dir = output_root / "compose-daily-review" / "compose-run-review"
            issues = json.loads((run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "editorial-review.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(issues))
            self.assertEqual("NEEDS_EDITOR_REVIEW", issues[0]["render_status"])
            self.assertEqual(1, len(review_items))

    def test_ingest_then_digest_then_compose_integration_produces_issue(self):
        ingest_run = load_ingest_run_module()
        digest_run = load_digest_run_module()
        compose_run = load_compose_run_module()
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
<item><guid>a1</guid><title>Python tooling update</title><link>https://example.com/posts/1?utm_source=x</link><description>Release notes and analysis.</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
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
                run_id="ingest-run-compose",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )
            self.assertEqual("SUCCEEDED", ingest_result["workflow_status"])

            digest_result = digest_run.run_pipeline(
                normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
                output_root=str(output_root),
                run_id="digest-run-compose",
            )
            self.assertEqual("SUCCEEDED", digest_result["workflow_status"])

            compose_result = compose_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                output_root=str(output_root),
                run_id="compose-from-digest",
                issue_date="2026-03-27",
            )

            run_dir = output_root / "compose-daily-review" / "compose-from-digest"
            issues = json.loads((run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", compose_result["workflow_status"])
            self.assertEqual(1, len(issues))
            self.assertEqual("compose-daily-review", manifest["workflow_name"])

    def test_missing_input_file_marks_workflow_failed(self):
        compose_run = load_compose_run_module()
        with workspace_tempdir() as tmp:
            output_root = tmp / "artifacts"

            result = compose_run.run_pipeline(
                digest_candidates_path=str(tmp / "missing.json"),
                output_root=str(output_root),
                run_id="compose-run-missing",
                issue_date="2026-03-27",
            )

            self.assertEqual("FAILED", result["workflow_status"])


if __name__ == "__main__":
    unittest.main()
