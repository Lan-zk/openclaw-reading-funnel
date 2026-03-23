# Implementation Plan: OpenClaw StoryPack Inbox Phase 1.3

Generated: 2026-03-23  
Status: Ready for macOS handoff

## Goal

这份计划不是为了在当前环境实现，而是为了在 macOS 上按 OpenClaw-native 方式落地：

- one editorial agent
- multiple narrow skills
- cron + standing orders + hooks
- explicit application state for business truth
- Telegram-first review loop
- Canvas/A2UI as first optional custom surface

## Build Order

1. Lock repository bootstrap contract
2. Lock runtime boundaries and ownership
3. Lock contracts and schemas
4. Build feed-to-StoryPack pipeline
5. Build Telegram-first delivery and feedback loop
6. Add memory write-through and monitoring
7. Add optional Canvas/A2UI surface
8. Only then evaluate whether a separate web UI is still needed

## Milestone 0: Lock Repository Bootstrap Contract

Before runtime implementation, freeze how this repo will be handed to OpenClaw.

### Deliverables

- repository layout spec
- install entrypoint spec
- README bootstrap flow
- agent/skills/config discovery rules
- bootstrap validation checklist

### Must-haves

- OpenClaw can discover agent config from the cloned repo
- OpenClaw can discover repo-bundled skills from the cloned repo
- runtime docs live inside the repo, not only in external notes
- the repo explains what is auto-installed versus what still needs environment secrets

### Output

- repo bootstrap contract
- suggested root directory layout
- first-run handoff checklist

## Milestone 1: Lock OpenClaw Runtime Boundaries First

Before any implementation, freeze what runs where.

### Deliverables

- `editorial` agent responsibility document
- skills inventory
- standing orders draft
- cron schedule draft
- hook policy draft
- state ownership note

### Output

- runtime architecture note
- primitive matrix: `skill / cron / hook / channel / memory / app state`
- security and credential boundary note

### Must-haves

- explicitly reject “many agents by default”
- define which side effects happen through Telegram/channel primitives
- define which data is app state versus OpenClaw memory

## Milestone 2: Lock Contracts And Schemas

Contracts come before surfaces.

### Deliverables

- `StoryPack` versioned entity schema
- `FeedbackEvent` schema
- projection rules
- `DeliveryArtifact` schema
- `ReviewQueueSnapshot` schema
- provenance record schema

### Output

- data model draft
- API or service contract draft
- state machine diagram

### Must-haves

- `expected_version` on every mutating review action
- `idempotency_key` on every side-effecting delivery/feedback path
- explicit `artifact_type` for `daily_digest` and `quiet_but_useful`

## Milestone 3: Feed To StoryPack Pipeline

Phase 1 starts with boring inputs.

### Deliverables

- `SourceConfig`
- feed fetch
- `RawItem`
- `CanonicalItem`
- extraction and normalization
- StoryPack build / merge / update

### Must-haves

- same `story_pack_id` increments `version` on meaningful change
- false merge enters `NEEDS_MANUAL_SPLIT`
- malformed content degrades visibly instead of disappearing silently
- parallelism is limited to fetch/extract, not final StoryPack ownership

### OpenClaw mapping

- `feed-ingest` skill
- `content-extract` skill
- `storypack-builder` skill
- scheduled by cron

## Milestone 4: Telegram-first Delivery And Feedback

Do not build a custom inbox before the Telegram loop works.

### Deliverables

- `daily_digest` artifact builder
- `quiet_but_useful` artifact builder
- Telegram sender
- Telegram inline action handling
- feedback event ingestion
- retry / dead-letter handling

### Must-haves

- retry reuses the same artifact
- same `selection_hash` and `content_hash` across retries
- inline `approve / reject / snooze / mark_for_publish`
- feedback actions resolve against `snapshot_id` and `expected_version`
- duplicate Telegram actions are idempotent

### OpenClaw mapping

- `digest-composer` skill
- `telegram-delivery` skill
- `feedback-sync` skill
- channel integration
- cron-triggered delivery run

## Milestone 5: Memory Write-Through And Learning Signals

Write-through is selective and explicit.

### Deliverables

- memory sync policy implementation note
- memory serialization format
- stable preference update logic
- learning signal projection note

### Must-haves

- app state remains source of truth
- only approved durable outcomes are written into OpenClaw memory
- noisy clickstream does not become durable memory
- memory sync failures do not corrupt StoryPack truth

### OpenClaw mapping

- `memory-sync` skill
- standing orders describing what may be remembered

## Milestone 6: Monitoring And Escalation

Operational quality has to exist before polish.

### Deliverables

- metrics list
- alert thresholds
- escalation states
- manual-review lane contract

### Must-haves

- false merge rate
- stale action conflict rate
- digest usefulness signal
- delivery failure rate
- quiet-but-useful effectiveness
- low-confidence/manual-review queue

### OpenClaw mapping

- hooks for lightweight trace and event logging
- cron-based health checks if needed

## Milestone 7: Optional Canvas / A2UI Surface

If a richer visual surface is needed, Canvas comes before a bespoke web app.

### Deliverables

- Canvas/A2UI surface sketch
- source health summary
- StoryPack review summary
- delivery history summary

### Must-haves

- consumes existing state contracts only
- does not invent new lifecycle rules
- keeps Telegram as a valid primary review surface

## Milestone 8: Re-evaluate Separate Web UI

Only after Telegram and optional Canvas are working should you decide whether `/sources /inbox /delivery` still needs to exist as a standalone app.

### Decision criteria

- does Telegram handle 80 percent of the daily review loop
- is Canvas enough for richer inspection
- is a separate app needed for product quality rather than operational convenience

## Suggested Skill Inventory

- `source-registry`
- `feed-ingest`
- `content-extract`
- `storypack-builder`
- `review-queue`
- `digest-composer`
- `telegram-delivery`
- `feedback-sync`
- `memory-sync`
- `lumina-sync` later

## Suggested File Ownership

```text
runtime/
  editorial agent bootstrap
  standing orders
  cron definitions
  hook definitions

core/
  storypack model
  feedback event model
  delivery artifact model
  queue snapshot model

pipeline/
  feed ingest
  canonicalization
  storypack builder
  digest composer
  memory sync

surfaces/
  telegram actions
  optional canvas surface
```

## Verification Order

1. feed ingestion works with stable source set
2. StoryPack versioning rejects stale writes
3. queue snapshot semantics hold across actions
4. Telegram digest sends exactly one artifact
5. Telegram inline actions create exactly one `FeedbackEvent`
6. retry reuses the same artifact without content drift
7. `quiet_but_useful` respects cooldown
8. memory write-through only mirrors approved durable outcomes
9. monitoring captures conflicts, failures, and manual-review lanes

## Risks To Watch Early

1. Using multiple agents where skills are enough
2. Treating OpenClaw memory as business storage
3. Building a custom web console before the Telegram loop works
4. Rebuilding digest content during retry instead of resending the same artifact
5. Letting Telegram actions bypass `snapshot_id` or `expected_version`
6. Writing noisy behavior into long-term memory

## Exit Criteria For Phase 1

- daily ingest and digest run via OpenClaw-native automation
- one editorial agent plus skills is enough for the full loop
- Telegram supports delivery and first-round review
- StoryPack, feedback, queue, and delivery all remain explicit app state
- selected conclusions are mirrored into OpenClaw memory intentionally
- manual-review and operational metrics exist
- no silent failure on fetch, merge, delivery, or feedback
