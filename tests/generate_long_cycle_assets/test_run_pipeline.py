import importlib.util
import json
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "generate-long-cycle-assets"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from support import workspace_tempdir


def load_run_module():
    module_path = SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("long_cycle_run_for_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


class RunPipelineTests(unittest.TestCase):
    def test_happy_path_produces_weekly_and_topic_assets(self):
        long_cycle_run = load_run_module()
        with workspace_tempdir() as tmp:
            assets_path = tmp / "knowledge-assets.json"
            issues_path = tmp / "daily-review-issues.json"
            output_root = tmp / "artifacts"
            write_json(
                assets_path,
                [
                    {
                        "knowledge_asset_id": "ka-1",
                        "title": "Prompt evaluation playbook",
                        "summary": "Repeatable prompt evaluation patterns and scorecards.",
                        "canonical_url": "https://example.com/prompt-eval-playbook",
                        "topic_tags": ["prompt", "evaluation", "playbook"],
                        "asset_type": "PATTERN",
                        "long_term_value_reason": "Reusable evaluation pattern.",
                        "stored_at": "2026-03-27T10:00:00+00:00",
                        "asset_status": "STORED",
                        "run_id": "curate-run",
                    },
                    {
                        "knowledge_asset_id": "ka-2",
                        "title": "Prompt evaluation checklist",
                        "summary": "Checklist for replayable prompt evaluation workflows.",
                        "canonical_url": "https://example.com/prompt-eval-checklist",
                        "topic_tags": ["prompt", "evaluation", "checklist"],
                        "asset_type": "PLAYBOOK",
                        "long_term_value_reason": "Stable checklist for future prompt work.",
                        "stored_at": "2026-03-27T10:05:00+00:00",
                        "asset_status": "STORED",
                        "run_id": "curate-run",
                    },
                ],
            )
            write_json(
                issues_path,
                [
                    {
                        "daily_review_issue_id": "dri-1",
                        "issue_date": "2026-03-27",
                        "sections": {
                            "今日大事": [
                                {
                                    "headline": "Prompt evaluation patterns mature",
                                    "summary": "Prompt evaluation is becoming a repeatable engineering practice.",
                                }
                            ],
                            "主题深挖": [],
                        },
                        "top_themes": ["Prompt Evaluation", "Evaluation Workflow"],
                        "editorial_notes": [],
                        "source_digest_candidate_ids": ["dc-1", "dc-2"],
                        "render_status": "COMPOSED",
                        "run_id": "compose-run",
                    }
                ],
            )

            result = long_cycle_run.run_pipeline(
                knowledge_assets_path=str(assets_path),
                daily_review_issues_path=str(issues_path),
                output_root=str(output_root),
                run_id="long-cycle-happy",
            )

            run_dir = output_root / "generate-long-cycle-assets" / "long-cycle-happy"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "author-review.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual({"WEEKLY", "TOPIC"}, {item["asset_scope"] for item in assets})
            self.assertEqual([], review_items)

    def test_empty_result_path_returns_success_with_empty_assets(self):
        long_cycle_run = load_run_module()
        with workspace_tempdir() as tmp:
            assets_path = tmp / "knowledge-assets.json"
            issues_path = tmp / "daily-review-issues.json"
            output_root = tmp / "artifacts"
            write_json(assets_path, [])
            write_json(
                issues_path,
                [
                    {
                        "daily_review_issue_id": "dri-empty",
                        "issue_date": "2026-03-27",
                        "sections": {"今日大事": [], "主题深挖": []},
                        "top_themes": [],
                        "editorial_notes": [],
                        "source_digest_candidate_ids": [],
                        "render_status": "COMPOSED",
                        "run_id": "compose-run",
                    }
                ],
            )

            result = long_cycle_run.run_pipeline(
                knowledge_assets_path=str(assets_path),
                daily_review_issues_path=str(issues_path),
                output_root=str(output_root),
                run_id="long-cycle-empty",
            )

            run_dir = output_root / "generate-long-cycle-assets" / "long-cycle-empty"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "author-review.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual([], assets)
            self.assertEqual([], review_items)
            self.assertIn("SUCCESS_EMPTY", {item["status"] for item in manifest["step_results"]})

    def test_review_path_produces_author_review_without_failure(self):
        long_cycle_run = load_run_module()
        with workspace_tempdir() as tmp:
            assets_path = tmp / "knowledge-assets.json"
            issues_path = tmp / "daily-review-issues.json"
            output_root = tmp / "artifacts"
            write_json(
                assets_path,
                [
                    {
                        "knowledge_asset_id": "ka-review-1",
                        "title": "Prompt workflow note",
                        "summary": "A short note about prompt workflows.",
                        "canonical_url": "https://example.com/prompt-note",
                        "topic_tags": ["prompt"],
                        "asset_type": "WATCH_ITEM",
                        "long_term_value_reason": "Interesting but still early.",
                        "stored_at": "2026-03-27T10:00:00+00:00",
                        "asset_status": "STORED",
                        "run_id": "curate-run",
                    }
                ],
            )
            write_json(
                issues_path,
                [
                    {
                        "daily_review_issue_id": "dri-review",
                        "issue_date": "2026-03-27",
                        "sections": {
                            "今日大事": [
                                {
                                    "headline": "Prompt workflow experiments continue",
                                    "summary": "The theme appears, but evidence is still thin.",
                                }
                            ]
                        },
                        "top_themes": ["Prompt Workflow"],
                        "editorial_notes": [],
                        "source_digest_candidate_ids": ["dc-r1"],
                        "render_status": "COMPOSED",
                        "run_id": "compose-run",
                    }
                ],
            )

            result = long_cycle_run.run_pipeline(
                knowledge_assets_path=str(assets_path),
                daily_review_issues_path=str(issues_path),
                output_root=str(output_root),
                run_id="long-cycle-review",
            )

            run_dir = output_root / "generate-long-cycle-assets" / "long-cycle-review"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "author-review.json").read_text(encoding="utf-8"))
            failures = json.loads((run_dir / "long-cycle-failures.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual([], assets)
            self.assertGreaterEqual(len(review_items), 1)
            self.assertEqual([], failures)

    def test_partial_success_keeps_weekly_asset_when_topic_assembly_fails(self):
        long_cycle_run = load_run_module()
        with workspace_tempdir() as tmp:
            assets_path = tmp / "knowledge-assets.json"
            issues_path = tmp / "daily-review-issues.json"
            output_root = tmp / "artifacts"
            write_json(
                assets_path,
                [
                    {
                        "knowledge_asset_id": "ka-partial-1",
                        "title": "Browser automation pattern",
                        "summary": "Stable browser automation practices for regression testing.",
                        "canonical_url": "https://example.com/browser-pattern",
                        "topic_tags": ["browser", "automation", "pattern"],
                        "asset_type": "PATTERN",
                        "long_term_value_reason": "Strong reusable pattern.",
                        "stored_at": "2026-03-27T10:00:00+00:00",
                        "asset_status": "STORED",
                        "run_id": "curate-run",
                    },
                    {
                        "knowledge_asset_id": "ka-partial-2",
                        "title": "Browser automation checklist",
                        "summary": "Checklist for stable browser automation.",
                        "canonical_url": "https://example.com/browser-checklist",
                        "topic_tags": ["browser", "automation", "checklist"],
                        "asset_type": "PLAYBOOK",
                        "long_term_value_reason": "Supportive checklist for the same theme.",
                        "stored_at": "2026-03-27T10:05:00+00:00",
                        "asset_status": "STORED",
                        "run_id": "curate-run",
                    },
                ],
            )
            write_json(
                issues_path,
                [
                    {
                        "daily_review_issue_id": "dri-partial",
                        "issue_date": "2026-03-27",
                        "sections": {
                            "今日大事": [
                                {
                                    "headline": "Browser automation reliability improves",
                                    "summary": "Patterns and checklists are converging.",
                                }
                            ]
                        },
                        "top_themes": ["Browser Automation"],
                        "editorial_notes": [],
                        "source_digest_candidate_ids": ["dc-p1"],
                        "render_status": "COMPOSED",
                        "run_id": "compose-run",
                    }
                ],
            )

            result = long_cycle_run.run_pipeline(
                knowledge_assets_path=str(assets_path),
                daily_review_issues_path=str(issues_path),
                output_root=str(output_root),
                run_id="long-cycle-partial",
                runtime_overrides={"force_topic_bundle_failure": True},
            )

            run_dir = output_root / "generate-long-cycle-assets" / "long-cycle-partial"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            failures = json.loads((run_dir / "long-cycle-failures.json").read_text(encoding="utf-8"))

            self.assertEqual("PARTIAL_SUCCESS", result["workflow_status"])
            self.assertEqual({"WEEKLY"}, {item["asset_scope"] for item in assets})
            self.assertGreaterEqual(len(failures), 1)

    def test_failure_path_returns_failed_when_input_is_missing(self):
        long_cycle_run = load_run_module()
        with workspace_tempdir() as tmp:
            output_root = tmp / "artifacts"

            result = long_cycle_run.run_pipeline(
                knowledge_assets_path=str(tmp / "missing-assets.json"),
                daily_review_issues_path=str(tmp / "missing-issues.json"),
                output_root=str(output_root),
                run_id="long-cycle-failed",
            )

            self.assertEqual("FAILED", result["workflow_status"])
            self.assertEqual({}, result["artifact_paths"])


if __name__ == "__main__":
    unittest.main()
