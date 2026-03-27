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


class SequentialSkillCallTests(unittest.TestCase):
    def test_agent_like_skill_chain_produces_daily_review_issue(self):
        ingest_run = load_run_module("ingest-normalize", "ingest_run_chain")
        digest_run = load_run_module("digest-candidates", "digest_run_chain")
        compose_run = load_run_module("compose-daily-review", "compose_run_chain")

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
<item><guid>a1</guid><title>Python security advisory</title><link>https://example.com/posts/security?utm_source=x</link><description>Security analysis and remediation guidance.</description><pubDate>Wed, 27 Mar 2026 12:00:00 GMT</pubDate></item>
<item><guid>a2</guid><title>Open source tooling guide</title><link>https://example.com/posts/tooling</link><description>Guide to the latest open source tooling changes.</description><pubDate>Wed, 27 Mar 2026 11:00:00 GMT</pubDate></item>
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
                run_id="agent-ingest-run",
                runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
            )
            self.assertEqual("SUCCEEDED", ingest_result["workflow_status"])

            digest_result = digest_run.run_pipeline(
                normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
                output_root=str(output_root),
                run_id="agent-digest-run",
            )
            self.assertEqual("SUCCEEDED", digest_result["workflow_status"])

            compose_result = compose_run.run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                output_root=str(output_root),
                run_id="agent-compose-run",
                issue_date="2026-03-27",
            )
            self.assertEqual("SUCCEEDED", compose_result["workflow_status"])

            compose_run_dir = output_root / "compose-daily-review" / "agent-compose-run"
            issues = json.loads((compose_run_dir / "daily-review-issues.json").read_text(encoding="utf-8"))
            markdown = (compose_run_dir / "daily-review.md").read_text(encoding="utf-8")

            self.assertEqual(1, len(issues))
            self.assertEqual("2026-03-27", issues[0]["issue_date"])
            self.assertIn("# Daily Review - 2026-03-27", markdown)
            self.assertTrue(any(len(entries) > 0 for entries in issues[0]["sections"].values()))


if __name__ == "__main__":
    unittest.main()
