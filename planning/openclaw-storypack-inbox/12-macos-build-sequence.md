# macOS Build Sequence: OpenClaw StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: define the recommended execution order when turning this planning pack into a real repo and runtime on macOS

## Goal

Reduce implementation thrash by sequencing the work in the order that locks structure first and behavior second.

## Phase A: Create The Repository Skeleton

Create the directories and starter files defined in:

- `08-repo-file-skeleton.md`
- `09-root-readme-draft.md`
- `10-bootstrap-doc-drafts.md`
- `11-openclaw-runtime-file-drafts.md`

Exit condition:

- repo tree exists
- root README exists
- bootstrap docs exist
- `openclaw/` subtree exists

## Phase B: Lock Runtime-facing Docs In The Repo

Materialize the first runtime-facing markdown files:

- agent README and AGENT
- standing orders
- automation notes
- skill `SKILL.md` and `README.md` placeholders

Exit condition:

- OpenClaw can be pointed at the repo and find runtime paths without chat context

## Phase C: Lock Contracts Before Code

Use these docs as the direct input:

- `05-api-schema-contracts.md`
- `01-design-v1.2.md`
- `02-implementation-plan.md`

Implementation tasks:

- formalize schemas
- formalize service interfaces
- choose internal transport style

Exit condition:

- contracts are written in implementation artifacts
- no core lifecycle ambiguity remains

## Phase D: Build Feed To StoryPack Core

Implement in this order:

1. source registry
2. feed ingest
3. canonical extraction
4. StoryPack builder
5. queue snapshot builder

Exit condition:

- a dry run can produce StoryPacks and one queue snapshot from test feeds

## Phase E: Build Telegram-first Loop

Implement in this order:

1. digest artifact builder
2. Telegram delivery path
3. inline action parsing
4. feedback event creation
5. projection updates

Exit condition:

- one digest can be sent safely
- one inline action can be handled safely

## Phase F: Add Memory Write-through

Implement:

- memory serialization format
- write-through safety rules
- durable summary sync

Exit condition:

- approved durable outcomes can be mirrored without becoming source of truth

## Phase G: Add Monitoring And Recovery

Implement:

- delivery retry
- dead-letter handling
- merge escalation lanes
- health summary signals

Exit condition:

- failures are visible
- retries are safe
- manual-review lanes exist

## Phase H: Optional Canvas

Only if needed:

- current queue summary
- delivery history
- escalation list

Exit condition:

- richer inspection exists without inventing a second state model

## Phase I: Re-evaluate Separate Web UI

Only after the Telegram loop works well should you ask whether a dedicated web surface is still worth building.

## Recommended Validation Order

1. repo bootstrap validation
2. dry-run ingest
3. StoryPack version conflict behavior
4. digest artifact idempotency
5. Telegram inline action idempotency
6. memory write-through safety
7. failure visibility

## Common Ways To Go Wrong

- building code before the repo bootstrap shape is stable
- adding extra agents too early
- mixing business truth into memory files
- inventing a richer UI before Telegram works
- skipping validation of idempotency and conflict behavior

## Completion Signal

This planning pack is implementation-ready when:

- repo shape is fixed
- bootstrap docs exist
- runtime docs exist
- contracts are fixed
- test bar is fixed
- the macOS session no longer needs to redesign the system before writing code

## Final Note

At this point, the next session should stop expanding docs and start materializing the repo shape itself.
