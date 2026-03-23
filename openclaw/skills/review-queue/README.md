# review-queue

Owns queue snapshot generation and progression rules.

## Pipeline Position

- downstream of `storypack-builder`
- upstream of `digest-composer` and `feedback-sync`

## Interacts With

- `ReviewQueueSnapshot`
- story status projections
- Telegram and future UI snapshot semantics

## Later Implementation Files

- snapshot builder
- queue ordering policy
- projection helpers for queue advancement
