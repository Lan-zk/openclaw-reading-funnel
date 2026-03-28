import shutil
import uuid
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import sys


WORK_TMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp-tests"
WORK_TMP_ROOT.mkdir(exist_ok=True)


@contextmanager
def workspace_tempdir():
    tmp = WORK_TMP_ROOT / f"case-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=False)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_ingest_run_module(module_name: str = "ingest_run_for_tests"):
    skill_dir = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
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
