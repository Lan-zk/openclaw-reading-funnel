import importlib.util
import json
import sys
import unittest
from pathlib import Path


CURATE_SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "curate-retain"
if str(CURATE_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(CURATE_SKILL_DIR))
CURATE_SCRIPT_DIR = CURATE_SKILL_DIR / "scripts"
if str(CURATE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CURATE_SCRIPT_DIR))

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


def load_curate_run_module():
    module_path = CURATE_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("curate_run_for_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_compose_run_module():
    module_path = COMPOSE_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("compose_run_for_curate_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_digest_run_module():
    module_path = DIGEST_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("digest_run_for_curate_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_ingest_run_module():
    module_path = INGEST_SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("ingest_run_for_curate_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunPipelineTests(unittest.TestCase):
    def test_queue_only_run_produces_success_with_empty_decisions(self):
        curate_run = load_curate_run_module()
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
                            "cluster_confidence": 0.95,
                            "display_title": "LLM evaluation patterns",
                            "display_summary": "A practical evaluation workflow for LLM systems.",
                            "canonical_url": "https://example.com/llm-evals",
                            "quality_score": 0.91,
                            "freshness_score": 0.82,
                            "digest_score": 0.89,
                            "noise_flags": [],
                            "needs_review": False,
                            "digest_status": "KEPT",
                            "run_id": "digest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = curate_run.run_pipeline(
                digest_candidates_path=str(input_path),
                output_root=str(output_root),
                run_id="curate-run-queue-only",
            )

            run_dir = output_root / "curate-retain" / "curate-run-queue-only"
            queue_items = json.loads((run_dir / "read-queue.json").read_text(encoding="utf-8"))
            decisions = json.loads((run_dir / "retention-decisions.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "step-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(queue_items))
            self.assertEqual([], decisions)
            self.assertEqual("SUCCESS_EMPTY", manifest["step_results"][1]["status"])

    def test_keep_decision_produces_decision_asset_and_signal_artifacts(self):
        curate_run = load_curate_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "digest-candidates.json"
            decision_path = tmp / "human-decisions.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "digest_candidate_id": "dc-keep",
                            "normalized_candidate_ids": ["nc-keep"],
                            "primary_normalized_candidate_id": "nc-keep",
                            "cluster_type": "SINGLE",
                            "cluster_confidence": 0.97,
                            "display_title": "Practical browser automation patterns",
                            "display_summary": "Patterns for stable browser automation and replayable QA.",
                            "canonical_url": "https://example.com/browser-automation-patterns",
                            "quality_score": 0.95,
                            "freshness_score": 0.80,
                            "digest_score": 0.92,
                            "noise_flags": [],
                            "needs_review": False,
                            "digest_status": "KEPT",
                            "run_id": "digest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            decision_path.write_text(
                json.dumps(
                    [
                        {
                            "target_type": "DIGEST_CANDIDATE",
                            "target_id": "dc-keep",
                            "decision": "KEEP",
                            "confidence": 0.93,
                            "reason_tags": ["ACTIONABLE_PRACTICE", "IMPLEMENTATION_PATTERN"],
                            "reason_text": "This is a reusable engineering pattern worth long-term retrieval.",
                            "decision_by": "tester",
                            "decision_at": "2026-03-27T12:00:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = curate_run.run_pipeline(
                digest_candidates_path=str(input_path),
                human_decisions_path=str(decision_path),
                output_root=str(output_root),
                run_id="curate-run-happy",
            )

            run_dir = output_root / "curate-retain" / "curate-run-happy"
            decisions = json.loads((run_dir / "retention-decisions.json").read_text(encoding="utf-8"))
            assets = json.loads((run_dir / "knowledge-assets.json").read_text(encoding="utf-8"))
            signals = json.loads((run_dir / "preference-signals.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(decisions))
            self.assertEqual("KEEP", decisions[0]["decision"])
            self.assertEqual(1, len(assets))
            self.assertEqual("PATTERN", assets[0]["asset_type"])
            self.assertGreaterEqual(len(signals), 1)
            self.assertTrue(any(signal["signal_type"] == "TOPIC_PREFERENCE" for signal in signals))

    def test_drop_decision_is_recorded_without_becoming_failure(self):
        curate_run = load_curate_run_module()
        with workspace_tempdir() as tmp:
            input_path = tmp / "digest-candidates.json"
            decision_path = tmp / "human-decisions.json"
            output_root = tmp / "artifacts"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "digest_candidate_id": "dc-drop",
                            "normalized_candidate_ids": ["nc-drop"],
                            "primary_normalized_candidate_id": "nc-drop",
                            "cluster_type": "SINGLE",
                            "cluster_confidence": 0.61,
                            "display_title": "Thin reposted summary",
                            "display_summary": "Mostly a repost without additional depth.",
                            "canonical_url": "https://example.com/repost",
                            "quality_score": 0.44,
                            "freshness_score": 0.70,
                            "digest_score": 0.51,
                            "noise_flags": [],
                            "needs_review": True,
                            "digest_status": "NEEDS_REVIEW",
                            "run_id": "digest-run",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            decision_path.write_text(
                json.dumps(
                    [
                        {
                            "target_type": "DIGEST_CANDIDATE",
                            "target_id": "dc-drop",
                            "decision": "DROP",
                            "confidence": 0.88,
                            "reason_tags": ["REPOST_WITHOUT_VALUE", "LOW_INFORMATION_DENSITY"],
                            "reason_text": "No additional long-term value beyond existing knowledge.",
                            "decision_by": "tester",
                            "decision_at": "2026-03-27T12:00:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = curate_run.run_pipeline(
                digest_candidates_path=str(input_path),
                human_decisions_path=str(decision_path),
                output_root=str(output_root),
                run_id="curate-run-drop",
            )

            run_dir = output_root / "curate-retain" / "curate-run-drop"
            decisions = json.loads((run_dir / "retention-decisions.json").read_text(encoding="utf-8"))
            failures = json.loads((run_dir / "curation-failures.json").read_text(encoding="utf-8"))
            assets = json.loads((run_dir / "knowledge-assets.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", result["workflow_status"])
            self.assertEqual(1, len(decisions))
            self.assertEqual("DROP", decisions[0]["decision"])
            self.assertEqual([], failures)
            self.assertEqual([], assets)

    def test_ingest_then_digest_then_compose_then_curate_integration_produces_keep_asset(self):
        ingest_run = load_ingest_run_module()
        digest_run = load_digest_run_module()
        compose_run = load_compose_run_module()
        curate_run = load_curate_run_module()
        with workspace_tempdir() as tmp:
            config_path = tmp / "sources.json"
            decision_path = tmp / "human-decisions.json"
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
<item><guid>a1</guid><title>LLM prompt evaluation playbook</title><link>https://example.com/posts/evals?utm_source=x</link><description>Reusable evaluation and review patterns for prompt systems.</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
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
                run_id="ingest-run-curate",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )
            self.assertEqual("SUCCEEDED", ingest_result["workflow_status"])

            digest_result = digest_run.run_pipeline(
                normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
                output_root=str(output_root),
                run_id="digest-run-curate",
            )
            self.assertEqual("SUCCEEDED", digest_result["workflow_status"])

            compose_result = compose_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                output_root=str(output_root),
                run_id="compose-run-curate",
                issue_date="2026-03-27",
            )
            self.assertEqual("SUCCEEDED", compose_result["workflow_status"])

            compose_run_dir = output_root / "compose-daily-review" / "compose-run-curate"
            issues = json.loads((compose_run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            digest_run_dir = output_root / "digest-candidates" / "digest-run-curate"
            digest_candidates = json.loads((digest_run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            target_id = digest_candidates[0]["digest_candidate_id"]

            decision_path.write_text(
                json.dumps(
                    [
                        {
                            "target_type": "DIGEST_CANDIDATE",
                            "target_id": target_id,
                            "decision": "KEEP",
                            "confidence": 0.91,
                            "reason_tags": ["LONG_TERM_REFERENCE", "DECISION_INPUT"],
                            "reason_text": "Useful as a durable reference for future LLM evaluation decisions.",
                            "decision_by": "tester",
                            "decision_at": "2026-03-27T13:30:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            curate_result = curate_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                daily_review_issue_path=str(compose_run_dir / "daily-review-issues.json"),
                human_decisions_path=str(decision_path),
                output_root=str(output_root),
                run_id="curate-from-compose",
            )

            curate_run_dir = output_root / "curate-retain" / "curate-from-compose"
            assets = json.loads((curate_run_dir / "knowledge-assets.json").read_text(encoding="utf-8"))

            self.assertEqual("SUCCEEDED", curate_result["workflow_status"])
            self.assertEqual(1, len(issues))
            self.assertEqual(1, len(assets))
            self.assertEqual("REFERENCE_NOTE", assets[0]["asset_type"])

    def test_missing_input_file_marks_workflow_failed(self):
        curate_run = load_curate_run_module()
        with workspace_tempdir() as tmp:
            output_root = tmp / "artifacts"

            result = curate_run.run_pipeline(
                digest_candidates_path=str(tmp / "missing.json"),
                output_root=str(output_root),
                run_id="curate-run-missing",
            )

            self.assertEqual("FAILED", result["workflow_status"])


if __name__ == "__main__":
    unittest.main()

