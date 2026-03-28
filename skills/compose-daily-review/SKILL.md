---
name: "compose-daily-review"
description: "Compose digest candidates into daily review issues, editorial review items, and human-readable run artifacts; use when the task is about daily review composition, section planning, theme synthesis, issue drafting, or readable daily-review rendering."
---

# compose-daily-review

This skill runs the `compose-daily-review` workflow MVP.

Use it when the task is about:
- turning digest candidates into a structured daily review
- grouping same-event candidates into one issue view
- assigning fixed daily review sections
- identifying top themes and deep-dive opportunities
- rendering a readable daily review draft

Do not use it when the task is about:
- source syncing or basic normalization
- candidate deduplication, extraction, or digest scoring
- long-term retention decisions
- long-cycle asset generation

Outputs:
- `daily-review-issues.json`
- `editorial-review.json`
- `daily-review-failures.json`
- `step-manifest.json`
- `daily-review-report.md`
- `daily-review.md`

Runtime entry:
- `run.py`

Implementation:
- `scripts/compose_daily_review/`

Reference:
- `references/design-authority.md`

Static eval data:
- `evals/trigger-evals.json`
- `evals/workflow-evals.json`
