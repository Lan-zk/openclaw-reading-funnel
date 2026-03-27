"""Compatibility entrypoint for the generate-long-cycle-assets skill."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from generate_long_cycle_assets.pipeline import (  # noqa: E402
    assemble_topic_asset_bundle,
    collect_period_assets,
    compose_weekly_assets,
    detect_hot_topics,
    evaluate_topic_writability,
    identify_long_signals,
    main,
    run_pipeline,
)


if __name__ == "__main__":
    raise SystemExit(main())
