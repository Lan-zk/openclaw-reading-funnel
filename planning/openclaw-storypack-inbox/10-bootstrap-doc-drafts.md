# Bootstrap Document Drafts: OpenClaw StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: draft the contents of the `bootstrap/` directory so the repo can explain installation and validation without extra chat context

## Draft: `bootstrap/README.md`

````markdown
# Bootstrap Docs

This directory explains how to bootstrap the OpenClaw StoryPack Inbox repository after cloning it.

Start in this order:

1. `install.md`
2. `env.example`
3. `repo-map.md`
4. `validate.md`

These files are meant for both human operators and OpenClaw-assisted setup flows.
````

## Draft: `bootstrap/install.md`

````markdown
# Install

This repo is structured so OpenClaw can discover the runtime layout from the repository itself.

## Install Intent

After cloning this repository, OpenClaw should be able to locate:

- the main editorial agent
- repo-bundled skills
- automation notes for cron and hooks
- memory conventions
- planning and contract docs

## Install Order

1. Read the repo root `README.md`
2. Inspect `openclaw/README.md`
3. Inspect `openclaw/agents/editorial/`
4. Inspect `openclaw/skills/`
5. Inspect `openclaw/automation/`
6. Review `bootstrap/env.example`
7. Run the validation flow in `bootstrap/validate.md`

## Required Manual Inputs

The repository should remain structurally self-contained. The only expected manual inputs are environment-specific values such as:

- Telegram bot token
- Telegram chat or topic identifiers
- optional future private source credentials

## What This Install Should Not Require

- searching chat history for agent paths
- manually discovering skill locations from memory
- guessing which docs matter
- reconstructing the runtime layout from scattered notes
````

## Draft: `bootstrap/validate.md`

````markdown
# Validate

Use this checklist after bootstrap to confirm the repo is discoverable and the Phase 1 runtime is coherent.

## Validation Goals

Confirm that:

1. the editorial agent is discoverable
2. required skills are discoverable
3. automation layout is readable
4. memory conventions are visible
5. a dry-run digest flow can be simulated safely

## Validation Checklist

### Repository discovery

- root `README.md` is present
- `openclaw/` subtree is present
- `bootstrap/` subtree is present
- planning pack is present

### Agent discovery

- `openclaw/agents/editorial/AGENT.md` exists
- standing orders exist
- memory policy exists

### Skill discovery

- each required Phase 1 skill has its own stable directory
- each required skill has `SKILL.md`

### Automation discovery

- cron docs exist
- hook policy exists

### Runtime safety

- source-of-truth rule is documented
- Telegram-first review rule is documented
- memory write-through policy is documented

## Dry-run validation

Before real delivery, validate the following path conceptually or in a safe test environment:

```text
Feed source discovered
  -> ingest skill discoverable
  -> StoryPack build path discoverable
  -> digest composer discoverable
  -> Telegram delivery path discoverable
  -> feedback sync path discoverable
```

## Success Criteria

Validation passes when a new operator can understand:

- where to start
- where the main agent lives
- where the skills live
- where Telegram delivery is defined
- where to continue into implementation
````

## Draft: `bootstrap/env.example`

````dotenv
# Telegram
TELEGRAM_BOT_TOKEN=replace_me
TELEGRAM_CHAT_ID=replace_me
TELEGRAM_TOPIC_ID=replace_me_optional

# Optional future source settings
DEFAULT_TIMEZONE=Asia/Shanghai
DIGEST_DELIVERY_WINDOW=09:00

# Notes
# - keep secrets out of committed real env files
# - this file documents variable names only
````

## Draft: `bootstrap/repo-map.md`

````markdown
# Repo Map

## Main Paths

- `README.md`
  - root install story
- `planning/openclaw-storypack-inbox/`
  - planning and contract pack
- `openclaw/agents/editorial/`
  - main editorial agent
- `openclaw/skills/`
  - Phase 1 repo-bundled skills
- `openclaw/automation/`
  - cron and hook layout
- `bootstrap/`
  - install and validation docs

## Most Important Runtime Locations

- agent identity: `openclaw/agents/editorial/AGENT.md`
- standing orders: `openclaw/agents/editorial/standing-orders/`
- skills: `openclaw/skills/`
- automation: `openclaw/automation/`

## Most Important Planning Locations

- design: `planning/openclaw-storypack-inbox/01-design-v1.2.md`
- runtime blueprint: `planning/openclaw-storypack-inbox/06-openclaw-runtime-blueprint.md`
- bootstrap contract: `planning/openclaw-storypack-inbox/07-repo-bootstrap-contract.md`
- repo skeleton: `planning/openclaw-storypack-inbox/08-repo-file-skeleton.md`
- API/schema contracts: `planning/openclaw-storypack-inbox/05-api-schema-contracts.md`
````

## Recommended Next Step

The next document after this should be:

- `11-openclaw-runtime-file-drafts.md`

That file should draft the actual contents of the first runtime-facing files under `openclaw/`.
