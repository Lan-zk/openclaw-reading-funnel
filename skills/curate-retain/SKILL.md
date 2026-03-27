---
name: "curate-retain"
description: "Record formal retention decisions, build long-term knowledge assets, and derive lightweight preference signals; use when the task is about human long-term value decisions, knowledge capture, retention ledgers, or post-review preference derivation."
---

# curate-retain

This skill runs the `curate-retain` workflow MVP.

Use it when the task is about:
- building a read queue for human retention review
- recording formal `KEEP`, `DROP`, `DEFER`, or `NEEDS_RECHECK` decisions
- storing high-value items as `KnowledgeAsset`
- deriving lightweight `PreferenceSignal` records from formal decisions

Do not use it when the task is about:
- source syncing or basic normalization
- candidate deduplication, extraction, or digest scoring
- daily review composition
- long-cycle asset generation

Outputs:
- `retention-decisions.json`
- `read-queue.json`
- `knowledge-assets.json`
- `preference-signals.json`
- `curation-failures.json`
- `step-manifest.json`
- `curation-report.md`

Runtime entry:
- `run.py`

Implementation:
- `scripts/curate_retain/`

Reference:
- `references/design-authority.md`

Static eval data:
- `evals/trigger-evals.json`
- `evals/workflow-evals.json`
