# source-registry

Owns feed source add, disable, and validation for Phase 1.

## Pipeline Position

- upstream of `feed-ingest`
- invoked by the editorial agent before daily ingest runs

## Interacts With

- `feed-ingest`
- source configuration and validation rules

## Later Implementation Files

- source config schema or validator
- registry adapter or persistence helper
- sample source fixtures if needed
