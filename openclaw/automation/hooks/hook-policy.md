# Hook Policy

Hooks may:

- write logs
- emit summaries
- append lightweight traces

Hooks may not:

- become the canonical state machine
- bypass StoryPack version checks
- bypass delivery idempotency rules
