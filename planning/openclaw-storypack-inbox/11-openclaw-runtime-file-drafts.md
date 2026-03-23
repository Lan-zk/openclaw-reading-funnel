# OpenClaw Runtime File Drafts: StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: draft the first runtime-facing files under `openclaw/` so the repo structure is not only folders but readable operating files

## Draft: `openclaw/README.md`

````markdown
# OpenClaw Runtime

This directory contains the OpenClaw-specific runtime layout for the StoryPack Inbox project.

## Contents

- `agents/`
  - main agent definitions and standing orders
- `skills/`
  - repo-bundled Phase 1 skills
- `automation/`
  - cron and hook docs or configs

## Runtime Principle

This project defaults to:

- one editorial agent
- multiple narrow skills
- Telegram-first delivery and review
- explicit application state as the business source of truth
````

## Draft: `openclaw/agents/editorial/AGENT.md`

````markdown
# Editorial Agent

## Mission

Run the daily editorial loop for the StoryPack Inbox system.

## Core Responsibilities

- orchestrate feed-to-StoryPack flow
- build or refresh review queue snapshots
- compose digest artifacts
- deliver through Telegram
- process Telegram feedback actions
- write selected durable outcomes into OpenClaw memory

## Boundaries

- do not treat memory as canonical StoryPack state
- do not create new agent-level sub-systems unless isolation is justified
- do not bypass version checks or idempotency rules

## Read Next

- `README.md`
- `standing-orders/daily-editorial.md`
- `standing-orders/memory-policy.md`
- `standing-orders/escalation-policy.md`
````

## Draft: `openclaw/agents/editorial/README.md`

````markdown
# Editorial Agent

This is the main runtime identity for Phase 1.

The editorial agent is responsible for the daily loop and should remain the default orchestrator unless a future isolation boundary clearly justifies more agents.
````

## Draft: `openclaw/agents/editorial/standing-orders/daily-editorial.md`

````markdown
# Daily Editorial Standing Orders

- Prefer deterministic workflow over broad autonomous planning.
- Use feed-based ingestion as the default Phase 1 input path.
- Treat Telegram as the first delivery and approval surface.
- Keep `StoryPack`, `FeedbackEvent`, `DeliveryArtifact`, and `ReviewQueueSnapshot` in explicit application state.
- Only escalate when ambiguity or failure crosses defined thresholds.
````

## Draft: `openclaw/agents/editorial/standing-orders/memory-policy.md`

````markdown
# Memory Policy

- OpenClaw memory is for durable editorial context, not canonical business state.
- Only write approved durable outcomes into memory.
- Do not write noisy clickstream, transient queue state, or low-confidence partials into memory.
- Memory files should point back conceptually to canonical application state.
````

## Draft: `openclaw/agents/editorial/standing-orders/escalation-policy.md`

````markdown
# Escalation Policy

Escalate when:

- StoryPack merge confidence is too low
- repeated delivery failures occur
- repeated stale-version conflicts occur
- memory write-through repeatedly fails
- evidence is contradictory enough to make auto-merge unsafe
````

## Draft: `openclaw/automation/README.md`

````markdown
# Automation

This directory contains automation notes or configs for cron jobs and hooks.

The intent is to make scheduled behavior and hook behavior discoverable from the repository.
````

## Draft: `openclaw/automation/cron/morning-digest.md`

````markdown
# Morning Digest

Run the primary daily editorial cycle:

1. ingest feeds
2. normalize candidates
3. build StoryPacks
4. generate queue snapshot
5. build digest artifact
6. send Telegram digest
````

## Draft: `openclaw/automation/cron/retry-recovery.md`

````markdown
# Retry Recovery

Inspect failed delivery artifacts and retry only when the retry contract allows resending the same artifact safely.
````

## Draft: `openclaw/automation/cron/maintenance.md`

````markdown
# Maintenance

Review run health, delivery anomalies, stale-action conflicts, and memory write failures after the main digest cycle.
````

## Draft: `openclaw/automation/hooks/hook-policy.md`

````markdown
# Hook Policy

Hooks may:

- write logs
- emit summaries
- append lightweight traces

Hooks may not:

- become the canonical state machine
- bypass StoryPack version checks
- bypass delivery idempotency rules
````

## Draft: `openclaw/skills/README.md`

````markdown
# Skills

This directory contains the repo-bundled Phase 1 skills for the StoryPack Inbox runtime.

Each skill should have:

- `SKILL.md`
- `README.md`

Each skill should explain its role, boundaries, inputs, outputs, and failure behavior.
````

## Recommended Next Step

The next document after this should be:

- `12-macos-build-sequence.md`

That file should convert the planning pack into the recommended order of work for the actual macOS implementation session.
