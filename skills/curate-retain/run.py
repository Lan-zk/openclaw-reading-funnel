"""Compatibility entrypoint for the curate-retain skill."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from curate_retain.pipeline import (  # noqa: E402
    build_read_queue,
    capture_human_decision,
    derive_long_term_tags,
    derive_preference_signals,
    main,
    persist_retention_decision,
    run_pipeline,
    store_knowledge_asset,
)


if __name__ == "__main__":
    raise SystemExit(main())
