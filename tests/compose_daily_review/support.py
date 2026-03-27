import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path


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
