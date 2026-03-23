# feedback-sync

## Job

Resolve Telegram review callbacks into canonical `FeedbackEvent` records and
projection updates.

## Expected Inputs

- Telegram inline action payload containing `story_pack_id`, `expected_version`,
  `snapshot_id`, `action`, and `idempotency_key`
- current StoryPack and queue state

## Expected Outputs

- one `FeedbackEvent`
- accepted projection update or safe conflict notice

## Boundaries

- validate snapshot semantics and versioned writes here
- duplicate callback with the same payload must be safe
- do not bypass canonical state transitions

## Failure Behavior

- return `STORYPACK_VERSION_CONFLICT` for stale writes
- return `INVALID_TELEGRAM_ACTION` for malformed actions
- return `IDEMPOTENCY_CONFLICT` for same key with different payload
