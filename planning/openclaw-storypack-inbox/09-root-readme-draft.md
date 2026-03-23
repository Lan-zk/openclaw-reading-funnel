# Root README Draft: OpenClaw StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: draft the repository root `README.md` that OpenClaw and human operators should read first

## Draft README

````markdown
# OpenClaw StoryPack Inbox

OpenClaw StoryPack Inbox is a personal editorial system for information overload.

It is designed to:

- ingest content from stable sources
- compress related updates into `StoryPack` objects
- deliver a daily high-signal digest through Telegram
- collect inline feedback directly in Telegram
- write selected durable conclusions back into OpenClaw memory

The repository is packaged so OpenClaw can bootstrap from the GitHub repo itself.

## What This Repo Contains

- a stable OpenClaw runtime layout
- repo-bundled skills required for Phase 1
- editorial agent configuration
- automation notes for cron and hooks
- planning and contract documents for later implementation

## Bootstrap Intent

This repository should be understandable by OpenClaw from the repo structure itself.

OpenClaw should be able to discover:

- the main editorial agent
- the repo-bundled skills
- the automation layout
- the memory conventions
- the validation flow

## Repository Map

```text
planning/openclaw-storypack-inbox/
  Product, architecture, test, bootstrap, and contract docs

openclaw/agents/editorial/
  Main editorial agent identity, standing orders, and memory conventions

openclaw/skills/
  Repo-local skills required for Phase 1

openclaw/automation/
  Cron and hook definitions or policy docs

bootstrap/
  Install flow, validation flow, environment contract, and repo map
```

## Phase 1 Runtime Model

Phase 1 uses:

- one editorial agent
- multiple narrow skills
- cron-driven digest runs
- Telegram-first delivery and review
- selective memory write-through

Phase 1 does not assume:

- browser-heavy crawling by default
- automatic social publishing
- a many-agent architecture by default
- a custom standalone admin web app as the first surface

## Install Story

Start here:

1. Read `bootstrap/install.md`
2. Read `bootstrap/env.example`
3. Inspect `openclaw/README.md`
4. Inspect `openclaw/agents/editorial/`
5. Inspect `openclaw/skills/`
6. Read `bootstrap/validate.md`

## OpenClaw-specific Paths

Main agent:

- `openclaw/agents/editorial/`

Skills:

- `openclaw/skills/`

Automation:

- `openclaw/automation/`

Planning pack:

- `planning/openclaw-storypack-inbox/`

Bootstrap docs:

- `bootstrap/`

## Required Environment Inputs

The repo should remain structurally self-contained, but some values are still environment-specific:

- Telegram bot token
- Telegram chat or topic identifiers
- optional source credentials if future private feeds are added
- local filesystem destination choices where needed

See:

- `bootstrap/env.example`

## Validation Flow

After bootstrap, validation should confirm:

1. the editorial agent is discoverable
2. required skills are discoverable
3. automation layout is readable
4. one dry-run digest flow can execute
5. Telegram delivery can be validated safely

See:

- `bootstrap/validate.md`

## Planning And Contracts

If you need the detailed planning pack, start with:

- `planning/openclaw-storypack-inbox/README.md`

Most important docs:

- `01-design-v1.2.md`
- `06-openclaw-runtime-blueprint.md`
- `07-repo-bootstrap-contract.md`
- `08-repo-file-skeleton.md`
- `05-api-schema-contracts.md`

## Source Of Truth Rule

OpenClaw memory is not the canonical business database.

Canonical state lives in explicit application-level objects such as:

- `StoryPack`
- `FeedbackEvent`
- `DeliveryArtifact`
- `ReviewQueueSnapshot`

OpenClaw memory is used only for selective write-through of durable editorial conclusions.

## Current Status

This repo is currently in planning-first shape.

The planning pack already defines:

- design boundaries
- runtime model
- schema contracts
- bootstrap contract
- repo file skeleton

Implementation should follow those docs instead of re-deciding the architecture from scratch.
````

## README Design Notes

This draft is intentionally optimized for both humans and OpenClaw:

- top section explains what the system does
- bootstrap section explains what OpenClaw should discover
- path map makes structure inferable
- environment section isolates what remains manual
- validation section makes success legible

## What This README Still Expects From Later Work

Later implementation should replace placeholders with actual repo paths once the runtime files exist:

- real `openclaw/` subtree
- real bootstrap docs
- real skill directories
- real validation flow

## Recommended Next Step

The next document after this should be:

- `10-bootstrap-doc-drafts.md`

That file should draft the contents of `bootstrap/install.md`, `bootstrap/validate.md`, `bootstrap/env.example`, and `bootstrap/repo-map.md`.
