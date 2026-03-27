import importlib.util
import json
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "compose-daily-review"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_run_module():
    module_path = SKILL_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("compose_run_surface_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillSurfaceTests(unittest.TestCase):
    def test_skill_shell_files_exist(self):
        self.assertTrue((SKILL_DIR / "SKILL.md").exists())
        self.assertTrue((SKILL_DIR / "run.py").exists())
        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").exists())
        self.assertTrue((SKILL_DIR / "references" / "design-authority.md").exists())
        self.assertTrue((SKILL_DIR / "evals" / "trigger-evals.json").exists())
        self.assertTrue((SKILL_DIR / "evals" / "workflow-evals.json").exists())

    def test_skill_markdown_declares_expected_name_and_outputs(self):
        content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('name: "compose-daily-review"', content)
        self.assertIn("daily-review-issues.json", content)
        self.assertIn("editorial-review.json", content)
        self.assertIn("daily-review.md", content)
        self.assertIn("scripts/compose_daily_review/", content)

    def test_agent_metadata_uses_skill_name_in_default_prompt(self):
        content = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("Compose Daily Review", content)
        self.assertIn("$compose-daily-review", content)

    def test_run_module_exports_workflow_entrypoints(self):
        run_module = load_run_module()
        self.assertTrue(callable(run_module.run_pipeline))
        self.assertTrue(callable(run_module.main))
        self.assertTrue(callable(run_module.merge_same_event_candidates))
        self.assertTrue(callable(run_module.compose_issue_structure))
        self.assertTrue(callable(run_module.render_human_readable_issue))

    def test_eval_files_cover_trigger_and_workflow_cases(self):
        trigger_evals = json.loads((SKILL_DIR / "evals" / "trigger-evals.json").read_text(encoding="utf-8"))
        workflow_evals = json.loads((SKILL_DIR / "evals" / "workflow-evals.json").read_text(encoding="utf-8"))
        self.assertIn("should_trigger", trigger_evals)
        self.assertIn("should_not_trigger", trigger_evals)
        self.assertIn("near_miss", trigger_evals)
        self.assertIn("happy_path", workflow_evals)
        self.assertIn("failure_path", workflow_evals)
        self.assertIn("empty_result_path", workflow_evals)


if __name__ == "__main__":
    unittest.main()
