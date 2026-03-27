"""Compatibility entrypoint for the ingest-normalize skill."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ingest_normalize.pipeline import (  # noqa: E402
    convert_to_feed,
    discover_sources,
    fetch_source_items,
    main,
    map_source_fields,
    normalize_candidates,
    persist_source_entries,
    prepare_output_directory,
    record_ingest_failures,
    run_pipeline,
    sync_source_window,
)


if __name__ == "__main__":
    raise SystemExit(main())
