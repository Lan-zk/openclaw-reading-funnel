# Retry Recovery

## Trigger Intent

Inspect failed delivery artifacts and retry only when the retry contract allows
resending the same artifact safely.

## Workflow

1. inspect eligible failed `DeliveryArtifact` records
2. verify the artifact is safe to resend without rebuild
3. submit another send attempt with a new send idempotency key
4. stop when the dead-letter threshold is reached

## Success Criteria

- retries reuse the same built artifact
- `selection_hash` and `content_hash` stay stable across retries
- dead-lettered artifacts remain visible for manual follow-up
