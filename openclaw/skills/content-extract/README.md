# content-extract

Owns canonical extraction, metadata normalization, and evidence capture.

## Pipeline Position

- downstream of `feed-ingest`
- upstream of `storypack-builder`

## Interacts With

- raw ingest output
- `EvidenceItem` generation
- canonical item normalization rules

## Later Implementation Files

- extractor or parser helpers
- canonical item schema helpers
- normalization fixtures and regression samples
