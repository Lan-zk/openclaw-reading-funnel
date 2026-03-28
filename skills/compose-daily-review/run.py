"""Compatibility entrypoint for the compose-daily-review skill."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from compose_daily_review.pipeline import (  # noqa: E402
    classify_sections,
    compose_issue_structure,
    detect_deep_dive_topics,
    identify_top_themes,
    main,
    merge_same_event_candidates,
    render_human_readable_issue,
    run_pipeline,
    score_daily_importance,
)


if __name__ == "__main__":
    raise SystemExit(main())
