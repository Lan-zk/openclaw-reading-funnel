# Test Plan: OpenClaw StoryPack Inbox Phase 1.3

Generated: 2026-03-23  
Source: synced to the OpenClaw-native design and implementation plan

## Test Strategy

Phase 1 should be tested against the actual runtime model now locked in:

- one editorial agent
- multiple skills
- cron-driven runs
- Telegram-first review loop
- explicit application state
- selective memory write-through

The test plan therefore focuses less on a hypothetical custom web app and more on:

- pipeline correctness
- Telegram action safety
- OpenClaw-native automation behavior
- state ownership boundaries

## Test Surfaces

### Primary surfaces

- feed source configuration flow
- scheduled ingest run
- StoryPack build/update pipeline
- Telegram digest delivery
- Telegram inline actions
- memory write-through
- monitoring and escalation signals

### Secondary surfaces

- optional Canvas / A2UI view
- optional later custom web UI

## Core User Journeys

### Journey 1: Daily high-signal digest

```text
Source configured
  -> feed fetched on schedule
  -> items normalized
  -> StoryPacks built
  -> queue snapshot created
  -> digest artifact built
  -> Telegram message delivered
```

Expected result:

- exactly one digest artifact is sent
- the delivered content matches the built artifact
- the selected StoryPacks are traceable via `selection_hash`

### Journey 2: Telegram-first approval loop

```text
Digest delivered
  -> user clicks approve/reject/snooze/mark_for_publish
  -> feedback event recorded
  -> projection updated
  -> queue advances safely
```

Expected result:

- one Telegram action creates one `FeedbackEvent`
- stale writes are rejected cleanly
- queue advancement uses the same `snapshot_id`

### Journey 3: Quiet but useful fallback

```text
No strong new StoryPacks
  -> fallback candidate selected
  -> quiet_but_useful artifact built
  -> rationale delivered to user
```

Expected result:

- fallback is treated as its own artifact type
- cooldown rules are enforced
- the user can see why this fallback was chosen

### Journey 4: Memory write-through

```text
StoryPack approved
  -> durable outcome selected
  -> memory sync runs
  -> approved summary written into OpenClaw memory
```

Expected result:

- app state remains source of truth
- only selected durable outcomes are mirrored
- memory sync failure does not corrupt business state

## Contract Tests

### StoryPack

- creating a new StoryPack produces `version = 1`
- adding meaningful evidence increments `version`
- low-impact metadata updates do not accidentally change user-visible truth unless intended
- false merge can enter `NEEDS_MANUAL_SPLIT`
- low-confidence packs remain reviewable or explicitly escalated

### FeedbackEvent

- every user action creates an auditable event
- projections are derived from the event stream
- duplicate action delivery does not create duplicate durable outcomes
- `marked_for_publish` updates publish intent without corrupting main status

### DeliveryArtifact

- retries reuse the same artifact
- retry does not silently rebuild different content
- `selection_hash` remains stable across retry
- `content_hash` remains stable across retry
- delayed acknowledgment does not create double success/failure state

### ReviewQueueSnapshot

- `current` and `next_up` come from the same snapshot
- a single stale item does not invalidate the whole snapshot
- queue progression removes the acted-on item and advances correctly
- Telegram actions and future UI actions share the same snapshot semantics

## OpenClaw-native Runtime Tests

### Agent and skill boundary tests

- the editorial flow can run with one main agent
- skills own task-local work rather than hidden session logic
- no phase 1 path requires extra agents to succeed

### Cron tests

- scheduled run triggers exactly one ingest/digest flow
- rerun after partial failure is safe
- cron-triggered delivery does not duplicate the same artifact

### Channel tests

- Telegram delivery succeeds to the intended target
- Telegram inline action round-trips into one event
- malformed or repeated Telegram callbacks are idempotent

### Hook tests

- hook-based logging does not mutate business truth
- hook failure does not break the core editorial loop

## State Ownership Tests

These tests exist to prevent the biggest architectural regression.

- no business-critical state exists only in OpenClaw memory
- restarting an agent/session does not lose StoryPack truth
- projection rebuild is possible from app state and event history
- memory write-through is additive context, not canonical state

## Edge Cases

- duplicate source added twice
- source disabled during active ingest
- feed timeout during cron run
- malformed item with missing author/date/body
- StoryPack with partial extraction only
- StoryPack updated while user is acting on an older version
- repeated Telegram callback after network delay
- fallback candidate selected within cooldown window
- memory sync target unavailable
- delivery succeeds but acknowledgment is delayed

## Critical Failure Modes

- feed timeout silently starves the queue
- normalization failure drops candidate content without visibility
- StoryPack version conflict silently overwrites a newer revision
- retry sends changed content under the same logical delivery
- Telegram action is applied twice
- memory sync failure poisons the main state transition
- low-confidence merge proceeds without escalation

## Monitoring Assertions

The following metrics should exist and be testable:

- false merge rate
- stale action conflict rate
- delivery failure rate
- digest usefulness signal
- quiet-but-useful usefulness rate
- publish intent precision

The following escalation lanes should exist and be testable:

- `NEEDS_MANUAL_SPLIT`
- low-confidence merge
- repeated delivery anomaly
- repeated stale-action conflict
- memory sync anomaly

## Suggested Verification Order

1. Feed ingestion and normalization
2. StoryPack versioning and merge behavior
3. Queue snapshot generation
4. Telegram digest delivery
5. Telegram inline feedback
6. Delivery retry idempotency
7. Quiet-but-useful cooldown
8. Memory write-through safety
9. Monitoring and escalation visibility

## Minimum Ship Bar For Phase 1

- no silent failure on ingest, merge, delivery, or feedback
- Telegram supports both delivery and first-round approval
- stale actions cannot overwrite newer StoryPack versions
- retries are idempotent
- selected outcomes can be mirrored into OpenClaw memory safely
- one editorial agent plus skills is sufficient for the full loop
