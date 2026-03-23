# feedback-sync

Owns Telegram action ingestion into `FeedbackEvent`.

## Pipeline Position

- downstream of `telegram-delivery` user actions
- feeds projection updates used by `review-queue`

## Interacts With

- `FeedbackEvent`
- queue advancement semantics
- Telegram inline callbacks

## Later Implementation Files

- callback parser
- action validator
- projection update helpers
