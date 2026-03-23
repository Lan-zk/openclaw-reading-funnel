# telegram-delivery

## Job

Send built delivery artifacts through Telegram and track retry-safe transport
state.

## Expected Inputs

- built `DeliveryArtifact`
- Telegram routing config and credentials
- send idempotency key

## Expected Outputs

- transport attempt updates on the same delivery artifact
- delivery success or failure status

## Boundaries

- reuse the same artifact on retry
- do not rebuild content during resend
- do not parse review callbacks here

## Failure Behavior

- mark send failure as `DELIVERY_SEND_FAILED`
- preserve the artifact for retry
- mark dead-letter when retry threshold is exceeded
