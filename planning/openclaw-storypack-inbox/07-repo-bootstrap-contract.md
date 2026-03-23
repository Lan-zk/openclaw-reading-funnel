# Repository Bootstrap Contract: OpenClaw StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: define how this GitHub repository should be packaged so OpenClaw can clone it and bootstrap the project from repo structure plus docs

## Problem This Solves

The target operating model is not:

- manually copy some files
- manually install some skills
- manually explain where the agent config lives

The target operating model is:

`Give OpenClaw the GitHub repository URL and let it discover how to install and run the project from the repository itself.`

That means the repo must behave like an installation bundle, not just a code container.

## Bootstrap Principle

The repository must be:

- self-describing
- self-locating
- self-documenting
- minimally hand-configured

OpenClaw should be able to infer:

- where the main agent definition lives
- where the repo-bundled skills live
- where automation config lives
- where memory conventions live
- what environment variables or secrets are still required
- what command or flow verifies a successful install

## Required Repository Capabilities

### 1. Root-level install story

The root `README.md` must answer:

- what this project is
- what OpenClaw should install
- where the OpenClaw-specific files live
- which parts are auto-discoverable
- which parts still require operator-provided secrets

### 2. Stable OpenClaw subtree

The repo must include a stable subtree for OpenClaw-specific assets.

Recommended shape:

```text
openclaw/
  agents/
  skills/
  automation/
  memory/
```

### 3. Repo-bundled skills

Skills required by this project should live inside the repo and be installable from the repo itself.

Design rule:

- do not assume later humans will remember a separate skill installation ritual
- if a skill is required for runtime, it belongs in the repository delivery model

### 4. Agent bootstrap files

The main editorial agent should be discoverable via a stable path and include:

- role/purpose
- standing orders
- memory conventions
- linked runtime docs if needed

### 5. Automation bootstrap files

The repo should make it obvious:

- what cron jobs exist
- what hooks exist
- what they are expected to do
- which ones are required versus optional

### 6. Validation path

The repo must explain what “successful install” looks like.

At minimum:

- OpenClaw can load the agent
- required skills are discoverable
- one dry-run digest flow can execute
- Telegram connectivity can be validated

## Recommended Repo Layout

```text
repo-root/
  README.md
  planning/
    openclaw-storypack-inbox/
  openclaw/
    agents/
      editorial/
        README.md
        standing-orders/
        memory/
    skills/
      source-registry/
      feed-ingest/
      content-extract/
      storypack-builder/
      review-queue/
      digest-composer/
      telegram-delivery/
      feedback-sync/
      memory-sync/
    automation/
      cron/
      hooks/
  bootstrap/
    install.md
    validate.md
    env.example
```

## File Responsibility Contract

### `README.md`

Human and OpenClaw-facing top-level entrypoint.

Should include:

- project summary
- install intent
- path map
- bootstrap order
- required secrets
- validation command or procedure

### `openclaw/agents/editorial/`

Main runtime identity.

Should include:

- agent purpose
- standing orders location
- memory conventions
- links to planning docs when needed

### `openclaw/skills/`

Repo-local runtime skills.

Should include:

- one directory per skill
- skill-local `SKILL.md`
- any skill-specific scripts/assets/templates

### `openclaw/automation/cron/`

Scheduled jobs and their intended purpose.

### `openclaw/automation/hooks/`

Hook definitions or hook policy notes.

### `bootstrap/install.md`

Step-by-step repo bootstrap explanation.

### `bootstrap/validate.md`

Post-install smoke test and acceptance checklist.

### `bootstrap/env.example`

Non-secret environment variable contract.

## Bootstrap Flow

Recommended bootstrap flow after OpenClaw receives the repository URL:

```text
Clone repo
  -> read root README
  -> discover openclaw/ subtree
  -> locate main agent definition
  -> locate repo-bundled skills
  -> locate automation config
  -> inspect env requirements
  -> validate install
  -> run first dry digest
```

## What Must Be Auto-discoverable

These should be inferable from the repo without asking the user to hunt:

- main agent path
- skill directory path
- automation path
- planning docs path
- bootstrap docs path

## What Can Still Be Manual

These can remain operator-supplied:

- Telegram bot token
- Telegram target/topic identifiers
- external feed credentials if any appear later
- local filesystem destination choices

### Rule

Manual inputs should be secrets or environment-specific values, not structural knowledge.

## Anti-patterns

The repo is not correctly packaged if any of these are true:

- skills required for runtime exist only in a different private path
- the main agent can only be found by reading chat history
- bootstrap requires tribal knowledge not present in the repo
- OpenClaw-specific config is scattered across unrelated folders
- planning docs describe a runtime structure the repo does not mirror

## Phase 1 Packaging Acceptance Checklist

- root README explains the install story
- repo includes a stable `openclaw/` subtree
- required skills are bundled in the repo
- main editorial agent is discoverable from the repo
- automation layout is discoverable from the repo
- validation path is documented
- only secrets remain manual

## Recommended Next Step

The next document after this should be:

- `08-repo-file-skeleton.md`

That file should turn this contract into an exact directory skeleton and starter file list so the macOS implementation session can create the repository shape without rethinking it.
