# feed-ingest

Owns feed-based candidate retrieval for Phase 1.

## Pipeline Position

- downstream of `source-registry`
- upstream of `content-extract`

## Interacts With

- enabled feed source config
- raw candidate item collection
- cron-driven morning digest runs

## Later Implementation Files

- feed client or parser helpers
- run ledger or fetch cursor helpers
- ingest fixtures and failure samples
