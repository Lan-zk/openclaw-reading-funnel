---
name: "generate-long-cycle-assets"
description: "Generate weekly or topic long-cycle assets from retained knowledge assets and daily review issues; use when the task is about weekly synthesis, topic bundle assembly, long-cycle themes, or reusable writing asset generation."
---

# generate-long-cycle-assets

This skill runs the `generate-long-cycle-assets` workflow MVP.

Use it when the task is about:
- turning retained knowledge and daily review issues into weekly assets
- assembling topic-scale writing bundles from accumulated material
- identifying recurring hot topics and long-cycle signals
- producing reusable long-cycle artifacts without re-fetching external sources

Do not use it when the task is about:
- source syncing or basic normalization
- candidate deduplication, extraction, or digest scoring
- daily review composition
- formal retention decisions or knowledge storage

Outputs:
- `long-cycle-assets.json`
- `author-review.json`
- `long-cycle-failures.json`
- `step-manifest.json`
- `long-cycle-report.md`

Runtime entry:
- `run.py`

Implementation:
- `scripts/generate_long_cycle_assets/`

Reference:
- `references/design-authority.md`

Static eval data:
- `evals/trigger-evals.json`
- `evals/workflow-evals.json`
