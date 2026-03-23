# digest-composer

Owns `daily_digest` and `quiet_but_useful` artifact composition.

## Pipeline Position

- downstream of `review-queue`
- upstream of `telegram-delivery`

## Interacts With

- `DeliveryArtifact`
- digest selection rules
- artifact hashing and idempotency expectations

## Later Implementation Files

- digest renderer or formatter
- artifact builder
- cooldown or selection policy helpers
