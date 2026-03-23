# Standing Orders

This directory contains durable editorial instructions that should survive
across runs.

These files define policy, not transient runtime state.

## Files

- `daily-editorial.md`
  - the daily operating loop and non-negotiable workflow rules
- `memory-policy.md`
  - what may be written into memory and what must remain in app state
- `escalation-policy.md`
  - when the agent must stop being clever and surface ambiguity or failure
