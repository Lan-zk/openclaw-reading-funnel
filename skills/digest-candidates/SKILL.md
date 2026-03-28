---
name: "digest-candidates"
description: "Transform normalized candidates into digest candidates, review items, and run artifacts; use when the task is about candidate deduplication, clustering, content extraction, summary generation, noise filtering, or digest pre-ranking."
---

# digest-candidates

This skill runs the `digest-candidates` workflow MVP.

Use it when the task is about:
- shrinking a normalized candidate pool into digest candidates
- deduplicating or clustering candidate items
- extracting lightweight readable content for screening
- generating summaries, review items, or digest pre-ranking

Do not use it when the task is about:
- source syncing or basic normalization
- daily review composition
- long-term retention decisions
- knowledge storage or long-cycle asset generation

Outputs:
- `digest-candidates.json`
- `digest-review.json`
- `digest-failures.json`
- `step-manifest.json`
- `digest-report.md`

Runtime entry:
- `run.py`

Implementation:
- `scripts/digest_candidates/`

Reference:
- `references/design-authority.md`

Static eval data:
- `evals/trigger-evals.json`
- `evals/workflow-evals.json`
