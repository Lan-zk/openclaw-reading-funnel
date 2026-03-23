# telegram-delivery

Owns Telegram delivery, resend safety, and delivery acknowledgments.

## Pipeline Position

- downstream of `digest-composer`
- adjacent to Telegram callback handling in `feedback-sync`

## Interacts With

- `DeliveryArtifact`
- Telegram transport and routing config
- retry and dead-letter policy

## Later Implementation Files

- Telegram sender adapter
- transport response mapper
- retry policy helpers
