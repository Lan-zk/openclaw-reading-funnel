import importlib.util
import json
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
    spec = importlib.util.spec_from_file_location("curate_run_surface_tests", module_path)
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
        self.assertIn('name: "curate-retain"', content)
        self.assertIn("retention-decisions.json", content)
        self.assertIn("knowledge-assets.json", content)
        self.assertIn("preference-signals.json", content)
        self.assertIn("scripts/curate_retain/", content)

    def test_agent_metadata_uses_skill_name_in_default_prompt(self):
        content = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("Curate Retain", content)
        self.assertIn("$curate-retain", content)

    def test_run_module_exports_workflow_entrypoints(self):
        run_module = load_run_module()
        self.assertTrue(callable(run_module.run_pipeline))
        self.assertTrue(callable(run_module.main))
        self.assertTrue(callable(run_module.build_read_queue))
        self.assertTrue(callable(run_module.capture_human_decision))
        self.assertTrue(callable(run_module.persist_retention_decision))
        self.assertTrue(callable(run_module.derive_long_term_tags))
        self.assertTrue(callable(run_module.store_knowledge_asset))
        self.assertTrue(callable(run_module.derive_preference_signals))

    def test_eval_files_cover_trigger_and_workflow_cases(self):
        trigger_evals = json.loads((SKILL_DIR / "evals" / "trigger-evals.json").read_text(encoding="utf-8"))
        workflow_evals = json.loads((SKILL_DIR / "evals" / "workflow-evals.json").read_text(encoding="utf-8"))
        self.assertIn("should_trigger", trigger_evals)
        self.assertIn("should_not_trigger", trigger_evals)
        self.assertIn("near_miss", trigger_evals)
        self.assertIn("happy_path", workflow_evals)
        self.assertIn("failure_path", workflow_evals)
        self.assertIn("queue_only_path", workflow_evals)


if __name__ == "__main__":
    unittest.main()

