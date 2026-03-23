# Hook Policy

## Hooks May

- write execution traces
- append operational logs
- emit lightweight alerts
- trigger post-run summaries

## Hooks May Not

- mutate canonical StoryPack truth directly
- bypass StoryPack version checks
- bypass queue snapshot semantics
- bypass delivery idempotency rules
- become the canonical state machine for review or delivery
