# Escalation Policy

Escalate when any of the following happens:

- StoryPack merge confidence is too low to auto-merge safely.
- Evidence is contradictory enough that the correct action is unclear.
- A potential false merge should be marked `STORYPACK_NEEDS_MANUAL_SPLIT`.
- Delivery retries hit the dead-letter threshold.
- Repeated stale-version conflicts suggest the queue view is drifting.
- Memory write-through repeatedly fails for otherwise approved outcomes.

## Safe Defaults

- suppress unsafe auto-approval paths
- preserve the canonical StoryPack outcome even if memory sync fails
- preserve the existing delivery artifact during retry investigation
- favor explicit operator review over hidden state mutation
