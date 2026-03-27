"""Compatibility entrypoint for the digest-candidates skill."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from digest_candidates.pipeline import (  # noqa: E402
    assemble_digest_candidates,
    canonicalize_url,
    check_quality,
    clean_content,
    compute_digest_score,
    exact_dedup,
    extract_main_content,
    filter_noise,
    generate_summary,
    main,
    near_duplicate_cluster,
    run_pipeline,
)


if __name__ == "__main__":
    raise SystemExit(main())
