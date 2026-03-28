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


class GenerateLongCycleChainTests(unittest.TestCase):
    def _load_modules(self, suffix: str):
        return {
            "ingest": load_run_module("ingest-normalize", f"ingest_run_{suffix}"),
            "digest": load_run_module("digest-candidates", f"digest_run_{suffix}"),
            "compose": load_run_module("compose-daily-review", f"compose_run_{suffix}"),
            "curate": load_run_module("curate-retain", f"curate_run_{suffix}"),
            "long_cycle": load_run_module("generate-long-cycle-assets", f"long_cycle_run_{suffix}"),
        }

    def _run_prefix(self, modules, tmp: Path, source_items: list[dict], decisions: list[dict] | None, suffix: str):
        config_path = tmp / "sources.json"
        output_root = tmp / "artifacts"
        rss_items = "".join(
            f"<item><guid>{item['guid']}</guid><title>{item['title']}</title><link>{item['link']}</link>"
            f"<description>{item['description']}</description><pubDate>{item['pub_date']}</pubDate></item>"
            for item in source_items
        )
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
                            "mock_response": f"<?xml version='1.0'?><rss version='2.0'><channel><title>demo</title>{rss_items}</channel></rss>",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        ingest_result = modules["ingest"].run_pipeline(
            source_config_path=str(config_path),
            output_root=str(output_root),
            run_id=f"agent-ingest-{suffix}",
            runtime_overrides={"now": "2026-03-27T13:00:00+00:00"},
        )
        digest_result = modules["digest"].run_pipeline(
            normalized_candidates_path=ingest_result["artifact_paths"]["normalized_candidates"],
            output_root=str(output_root),
            run_id=f"agent-digest-{suffix}",
        )
        compose_result = modules["compose"].run_pipeline(
            digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
            output_root=str(output_root),
            run_id=f"agent-compose-{suffix}",
            issue_date="2026-03-27",
        )
        if decisions is not None:
            decision_path = tmp / "human-decisions.json"
            digest_candidates = json.loads(
                Path(digest_result["artifact_paths"]["digest_candidates"]).read_text(encoding="utf-8")
            )
            resolved = []
            for decision in decisions:
                idx = decision.pop("digest_index")
                resolved.append(
                    {
                        **decision,
                        "target_type": "DIGEST_CANDIDATE",
                        "target_id": digest_candidates[idx]["digest_candidate_id"],
                    }
                )
            decision_path.write_text(json.dumps(resolved), encoding="utf-8")
            curate_result = modules["curate"].run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                daily_review_issue_path=compose_result["artifact_paths"]["daily_review_issues"],
                human_decisions_path=str(decision_path),
                output_root=str(output_root),
                run_id=f"agent-curate-{suffix}",
            )
        else:
            curate_result = modules["curate"].run_pipeline(
                digest_candidates_path=digest_result["artifact_paths"]["digest_candidates"],
                daily_review_issue_path=compose_result["artifact_paths"]["daily_review_issues"],
                output_root=str(output_root),
                run_id=f"agent-curate-{suffix}",
            )
        return output_root, compose_result, curate_result

    def test_agent_like_full_chain_happy_path_produces_long_cycle_assets(self):
        modules = self._load_modules("chain_long_cycle_happy")
        with workspace_tempdir() as tmp:
            output_root, compose_result, curate_result = self._run_prefix(
                modules,
                tmp,
                [
                    {
                        "guid": "a1",
                        "title": "Prompt evaluation playbook",
                        "link": "https://example.com/posts/prompt-playbook",
                        "description": "Reusable prompt evaluation playbook for production teams.",
                        "pub_date": "Wed, 27 Mar 2026 12:00:00 GMT",
                    },
                    {
                        "guid": "a2",
                        "title": "Prompt evaluation checklist",
                        "link": "https://example.com/posts/prompt-checklist",
                        "description": "Checklist for replayable prompt evaluation workflows.",
                        "pub_date": "Wed, 27 Mar 2026 11:30:00 GMT",
                    },
                ],
                [
                    {
                        "digest_index": 0,
                        "decision": "KEEP",
                        "confidence": 0.95,
                        "reason_tags": ["IMPLEMENTATION_PATTERN", "DECISION_INPUT"],
                        "reason_text": "Stable long-term prompt evaluation reference.",
                        "decision_by": "tester",
                        "decision_at": "2026-03-27T13:30:00+00:00",
                    },
                    {
                        "digest_index": 1,
                        "decision": "KEEP",
                        "confidence": 0.95,
                        "reason_tags": ["IMPLEMENTATION_PATTERN", "DECISION_INPUT"],
                        "reason_text": "Stable long-term prompt evaluation reference.",
                        "decision_by": "tester",
                        "decision_at": "2026-03-27T13:31:00+00:00",
                    },
                ],
                "long-cycle-happy",
            )

            long_cycle_result = modules["long_cycle"].run_pipeline(
                knowledge_assets_path=curate_result["artifact_paths"]["knowledge_assets"],
                daily_review_issues_path=compose_result["artifact_paths"]["daily_review_issues"],
                output_root=str(output_root),
                run_id="agent-long-cycle-happy",
            )

            self.assertEqual("SUCCEEDED", long_cycle_result["workflow_status"])
            run_dir = output_root / "generate-long-cycle-assets" / "agent-long-cycle-happy"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(assets), 1)

    def test_agent_like_full_chain_empty_path_produces_empty_long_cycle_result(self):
        modules = self._load_modules("chain_long_cycle_empty")
        with workspace_tempdir() as tmp:
            output_root, compose_result, curate_result = self._run_prefix(
                modules,
                tmp,
                [
                    {
                        "guid": "a1",
                        "title": "Short note",
                        "link": "https://example.com/posts/short-note",
                        "description": "Tiny update.",
                        "pub_date": "Wed, 27 Mar 2026 12:00:00 GMT",
                    }
                ],
                None,
                "long-cycle-empty",
            )

            long_cycle_result = modules["long_cycle"].run_pipeline(
                knowledge_assets_path=curate_result["artifact_paths"]["knowledge_assets"],
                daily_review_issues_path=compose_result["artifact_paths"]["daily_review_issues"],
                output_root=str(output_root),
                run_id="agent-long-cycle-empty",
            )

            self.assertEqual("SUCCEEDED", long_cycle_result["workflow_status"])
            run_dir = output_root / "generate-long-cycle-assets" / "agent-long-cycle-empty"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "author-review.json").read_text(encoding="utf-8"))
            self.assertEqual([], assets)
            self.assertEqual([], review_items)

    def test_agent_like_full_chain_review_path_produces_author_review_items(self):
        modules = self._load_modules("chain_long_cycle_review")
        with workspace_tempdir() as tmp:
            output_root, compose_result, curate_result = self._run_prefix(
                modules,
                tmp,
                [
                    {
                        "guid": "a1",
                        "title": "Prompt workflow note",
                        "link": "https://example.com/posts/prompt-note",
                        "description": "Early note about prompt workflow experiments.",
                        "pub_date": "Wed, 27 Mar 2026 12:00:00 GMT",
                    }
                ],
                [
                    {
                        "digest_index": 0,
                        "decision": "KEEP",
                        "confidence": 0.72,
                        "reason_tags": ["DECISION_INPUT"],
                        "reason_text": "Potentially useful, but still thin.",
                        "decision_by": "tester",
                        "decision_at": "2026-03-27T13:30:00+00:00",
                    }
                ],
                "long-cycle-review",
            )

            long_cycle_result = modules["long_cycle"].run_pipeline(
                knowledge_assets_path=curate_result["artifact_paths"]["knowledge_assets"],
                daily_review_issues_path=compose_result["artifact_paths"]["daily_review_issues"],
                output_root=str(output_root),
                run_id="agent-long-cycle-review",
            )

            self.assertEqual("SUCCEEDED", long_cycle_result["workflow_status"])
            run_dir = output_root / "generate-long-cycle-assets" / "agent-long-cycle-review"
            assets = json.loads((run_dir / "long-cycle-assets.json").read_text(encoding="utf-8"))
            review_items = json.loads((run_dir / "author-review.json").read_text(encoding="utf-8"))
            self.assertEqual([], assets)
            self.assertGreaterEqual(len(review_items), 1)

    def test_agent_like_full_chain_failure_path_surfaces_failed_result(self):
        modules = self._load_modules("chain_long_cycle_failed")
        with workspace_tempdir() as tmp:
            output_root, compose_result, curate_result = self._run_prefix(
                modules,
                tmp,
                [
                    {
                        "guid": "a1",
                        "title": "Prompt evaluation playbook",
                        "link": "https://example.com/posts/prompt-playbook",
                        "description": "Reusable prompt evaluation playbook for production teams.",
                        "pub_date": "Wed, 27 Mar 2026 12:00:00 GMT",
                    }
                ],
                [
                    {
                        "digest_index": 0,
                        "decision": "KEEP",
                        "confidence": 0.95,
                        "reason_tags": ["IMPLEMENTATION_PATTERN", "DECISION_INPUT"],
                        "reason_text": "Stable long-term prompt evaluation reference.",
                        "decision_by": "tester",
                        "decision_at": "2026-03-27T13:30:00+00:00",
                    }
                ],
                "long-cycle-failed",
            )

            long_cycle_result = modules["long_cycle"].run_pipeline(
                knowledge_assets_path=curate_result["artifact_paths"]["knowledge_assets"],
                daily_review_issues_path=str(tmp / "missing-daily-review-issues.json"),
                output_root=str(output_root),
                run_id="agent-long-cycle-failed",
            )

            self.assertEqual("FAILED", long_cycle_result["workflow_status"])


if __name__ == "__main__":
    unittest.main()
