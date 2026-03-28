---
name: "ingest-normalize"
description: "Ingest configured content sources, normalize them into source entries and normalized candidates, and emit JSON artifacts; use when the task is about source discovery, syncing, fetching, importing, or basic normalization."
---

# ingest-normalize

This skill runs the `ingest-normalize` workflow MVP.

Use it when the task is about:
- reading source configuration
- syncing or fetching sources
- importing feed items
- creating `SourceEntry` and `NormalizedCandidate`

Do not use it when the task is about:
- deduplication
- summary generation
- digest ranking or selection
- downstream workflow orchestration

Outputs:
- `source-entries.json`
- `normalized-candidates.json`
- `ingest-failures.json`
- `step-manifest.json`
- `ingest-report.json`

Runtime entry:
- `run.py`

Implementation:
- `scripts/ingest_normalize/`

Reference:
- `references/design-authority.md`

Static sample data:
- `data/source-adapters.example.json`
