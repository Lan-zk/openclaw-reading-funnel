import importlib.util
import json
import sys
import unittest
from pathlib import Path

from tests.compose_daily_review.support import workspace_tempdir


ROOT = Path(__file__).resolve().parents[2]


def load_run_module(skill_name: str, module_name: str):
    skill_dir = ROOT / "skills" / skill_name
    if str(skill_dir) not in sys.path:
        sys.path.insert(0, str(skill_dir))
    script_dir = skill_dir / "scripts"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    module_path = skill_dir / "run.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SequentialCurateRetainChainTests(unittest.TestCase):
    def test_agent_like_skill_chain_produces_retained_asset(self):
        ingest_run = load_run_module("ingest-normalize", "ingest_run_chain_curate")
        digest_run = load_run_module("digest-candidates", "digest_run_chain_curate")
        compose_run = load_run_module("compose-daily-review", "compose_run_chain_curate")
        curate_run = load_run_module("curate-retain", "curate_run_chain_curate")

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
<item><guid>a1</guid><title>Prompt evaluation reference</title><link>https://example.com/posts/prompt-evals?utm_source=x</link><description>Reusable evaluation guidance for prompt systems.</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
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
                run_id="chain-ingest-run",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )
            self.assertEqual("SUCCEEDED", ingest_result["workflow_status"])

            digest_result = digest_run.run_pipeline(
                normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
                output_root=str(output_root),
                run_id="chain-digest-run",
            )
            self.assertEqual("SUCCEEDED", digest_result["workflow_status"])

            compose_result = compose_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                output_root=str(output_root),
                run_id="chain-compose-run",
                issue_date="2026-03-27",
            )
            self.assertEqual("SUCCEEDED", compose_result["workflow_status"])

            digest_run_dir = output_root / "digest-candidates" / "chain-digest-run"
            digest_candidates = json.loads((digest_run_dir / "digest-candidates.json").read_text(encoding="utf-8"))
            decision_path.write_text(
                json.dumps(
                    [
                        {
                            "target_type": "DIGEST_CANDIDATE",
                            "target_id": digest_candidates[0]["digest_candidate_id"],
                            "decision": "KEEP",
                            "confidence": 0.9,
                            "reason_tags": ["LONG_TERM_REFERENCE", "DECISION_INPUT"],
                            "reason_text": "Reusable reference for future prompt evaluation work.",
                            "decision_by": "tester",
                            "decision_at": "2026-03-27T13:30:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            curate_result = curate_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                daily_review_issue_path=compose_result["artifact_paths"]["daily_review_issues"],
                human_decisions_path=str(decision_path),
                output_root=str(output_root),
                run_id="chain-curate-run",
            )
            self.assertEqual("SUCCEEDED", curate_result["workflow_status"])

            curate_run_dir = output_root / "curate-retain" / "chain-curate-run"
            assets = json.loads((curate_run_dir / "knowledge-assets.json").read_text(encoding="utf-8"))
            report = (curate_run_dir / "curation-report.md").read_text(encoding="utf-8")

            self.assertEqual(1, len(assets))
            self.assertIn("# curate-retain report", report)


if __name__ == "__main__":
    unittest.main()
