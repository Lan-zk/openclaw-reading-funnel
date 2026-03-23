# Morning Digest

## Trigger Intent

Run the primary daily editorial cycle once per day during the user's preferred
morning window.

## Workflow

1. fetch enabled feeds
2. normalize candidates into canonical items
3. build or refresh `StoryPack` state
4. generate one `ReviewQueueSnapshot`
5. build one `daily_digest` `DeliveryArtifact`
6. send the digest through Telegram

## Success Criteria

- the queue snapshot and digest artifact are built from the same review state
- Telegram delivery is attempted with an explicit idempotency key
- failures remain visible even if some sources succeed

## Failure Behavior

- per-source fetch failure does not erase other sources
- delivery failure preserves the built artifact for retry
