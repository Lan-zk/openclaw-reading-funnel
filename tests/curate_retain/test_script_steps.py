import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "curate-retain"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_run_module():
    module_path = SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("curate_run_script_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScriptStepTests(unittest.TestCase):
    def test_build_read_queue_prioritizes_daily_review_targets(self):
        curate_run = load_run_module()
        digest_candidates = [
            {
                "digest_candidate_id": "dc-1",
                "display_title": "Important item",
                "display_summary": "Worth retaining.",
                "canonical_url": "https://example.com/important",
                "digest_score": 0.92,
                "quality_score": 0.88,
                "needs_review": False,
                "digest_status": "KEPT",
                "run_id": "digest-run",
            },
            {
                "digest_candidate_id": "dc-2",
                "display_title": "Less urgent item",
                "display_summary": "Maybe useful later.",
                "canonical_url": "https://example.com/later",
                "digest_score": 0.62,
                "quality_score": 0.67,
                "needs_review": True,
                "digest_status": "NEEDS_REVIEW",
                "run_id": "digest-run",
            },
        ]
        daily_review_issue = [
            {
                "daily_review_issue_id": "dri-1",
                "issue_date": "2026-03-27",
                "sections": {
                    "今日大事": [
                        {
                            "entry_id": "dre-1",
                            "event_bundle_id": "bundle-1",
                            "headline": "Important item",
                            "source_digest_candidate_ids": ["dc-1"],
                        }
                    ]
                },
                "top_themes": [],
                "editorial_notes": [],
                "source_digest_candidate_ids": ["dc-1"],
                "render_status": "COMPOSED",
                "run_id": "compose-run",
            }
        ]

        queue_items, failures = curate_run.build_read_queue(digest_candidates, daily_review_issue, "curate-run")

        self.assertEqual([], failures)
        self.assertEqual(2, len(queue_items))
        self.assertEqual("dc-1", queue_items[0]["target_id"])
        self.assertEqual("HIGH", queue_items[0]["queue_priority"])

    def test_derive_long_term_tags_only_emits_assets_for_keep_decisions(self):
        curate_run = load_run_module()
        decisions = [
            {
                "retention_decision_id": "rd-keep",
                "target_type": "DIGEST_CANDIDATE",
                "target_id": "dc-keep",
                "decision": "KEEP",
                "confidence": 0.9,
                "reason_tags": ["ACTIONABLE_PRACTICE", "IMPLEMENTATION_PATTERN"],
                "reason_text": "Reusable pattern",
                "decision_at": "2026-03-27T12:00:00+00:00",
                "decision_by": "tester",
                "run_id": "curate-run",
            },
            {
                "retention_decision_id": "rd-drop",
                "target_type": "DIGEST_CANDIDATE",
                "target_id": "dc-drop",
                "decision": "DROP",
                "confidence": 0.8,
                "reason_tags": ["LOW_INFORMATION_DENSITY"],
                "reason_text": "Not worth keeping",
                "decision_at": "2026-03-27T12:00:00+00:00",
                "decision_by": "tester",
                "run_id": "curate-run",
            },
        ]
        snapshots = [
            {
                "target_type": "DIGEST_CANDIDATE",
                "target_id": "dc-keep",
                "title": "Browser automation pattern",
                "summary": "A practical pattern for browser testing.",
                "canonical_url": "https://example.com/browser-pattern",
                "source_digest_candidate_ids": ["dc-keep"],
                "run_id": "curate-run",
            }
        ]

        drafts, failures = curate_run.derive_long_term_tags(decisions, snapshots, "curate-run")

        self.assertEqual([], failures)
        self.assertEqual(1, len(drafts))
        self.assertEqual("dc-keep", drafts[0]["target_id"])
        self.assertEqual("PATTERN", drafts[0]["asset_type"])

    def test_derive_preference_signals_uses_retention_decision_as_canonical_origin(self):
        curate_run = load_run_module()
        decisions = [
            {
                "retention_decision_id": "rd-1",
                "target_type": "DIGEST_CANDIDATE",
                "target_id": "dc-1",
                "decision": "KEEP",
                "confidence": 0.94,
                "reason_tags": ["LONG_TERM_REFERENCE", "DECISION_INPUT"],
                "reason_text": "Good durable reference",
                "decision_at": "2026-03-27T12:00:00+00:00",
                "decision_by": "tester",
                "run_id": "curate-run",
            }
        ]
        assets = [
            {
                "knowledge_asset_id": "ka-1",
                "origin_retention_decision_id": "rd-1",
                "title": "Prompt eval reference",
                "summary": "Reusable evaluation reference.",
                "canonical_url": "https://example.com/prompt-eval-reference",
                "topic_tags": ["prompt-evals"],
                "asset_type": "REFERENCE_NOTE",
                "long_term_value_reason": "Useful reference",
                "stored_at": "2026-03-27T12:01:00+00:00",
                "asset_status": "STORED",
                "run_id": "curate-run",
            }
        ]

        signals, failures = curate_run.derive_preference_signals(decisions, assets, "curate-run")

        self.assertEqual([], failures)
        self.assertGreaterEqual(len(signals), 1)
        self.assertEqual("rd-1", signals[0]["origin_retention_decision_id"])
        self.assertEqual("rd-1", signals[0]["derived_from"]["origin_retention_decision_id"])


if __name__ == "__main__":
    unittest.main()
