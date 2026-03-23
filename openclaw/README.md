# OpenClaw Runtime

This directory contains the OpenClaw-specific runtime layout for the StoryPack
Inbox project.

## Contents

- `agents/`
  - main agent definitions, standing orders, and memory conventions
- `skills/`
  - repo-bundled Phase 1 skills that map to the editorial workflow
- `automation/`
  - cron and hook docs that describe scheduled behavior and operational
    boundaries

## Runtime Topology

Phase 1 is intentionally small:

- one editorial agent orchestrates the loop
- narrow skills own bounded workflow steps
- cron triggers the daily and recovery flows
- Telegram is the first delivery and review surface
- OpenClaw memory stores mirrored durable context, not canonical business truth

## Hard Rules

- `StoryPack`, `FeedbackEvent`, `DeliveryArtifact`, and `ReviewQueueSnapshot`
  remain in explicit application state
- review actions require `story_pack_id`, `expected_version`, `snapshot_id`, and
  `idempotency_key`
- retries reuse the same delivery artifact rather than rebuilding new content
- extra agents are deferred until there is a real isolation requirement

## Read Next

- `agents/editorial/AGENT.md`
- `skills/README.md`
- `automation/README.md`
- `../planning/openclaw-storypack-inbox/06-openclaw-runtime-blueprint.md`
