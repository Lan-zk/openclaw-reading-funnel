# Repository File Skeleton: OpenClaw StoryPack Inbox

Generated: 2026-03-23  
Status: Draft  
Purpose: define the exact repository skeleton and starter file inventory for the OpenClaw-installable repo

## Skeleton Goal

This file turns the bootstrap contract into a concrete repository shape.

It answers:

- what top-level directories should exist
- which files are required for Phase 1
- which files are docs versus runtime files
- which files are templates that later implementation should fill in

## Recommended Repository Tree

```text
repo-root/
  README.md
  LICENSE
  .gitignore

  planning/
    openclaw-storypack-inbox/
      README.md
      01-design-v1.2.md
      02-implementation-plan.md
      03-test-plan.md
      04-openclaw-patterns-evaluation.md
      05-api-schema-contracts.md
      06-openclaw-runtime-blueprint.md
      07-repo-bootstrap-contract.md
      08-repo-file-skeleton.md

  bootstrap/
    README.md
    install.md
    validate.md
    env.example
    repo-map.md

  openclaw/
    README.md

    agents/
      editorial/
        README.md
        AGENT.md
        standing-orders/
          README.md
          daily-editorial.md
          memory-policy.md
          escalation-policy.md
        memory/
          README.md
          editorial/
            preferences.md
            approved-storypacks/

    skills/
      README.md
      source-registry/
        SKILL.md
        README.md
      feed-ingest/
        SKILL.md
        README.md
      content-extract/
        SKILL.md
        README.md
      storypack-builder/
        SKILL.md
        README.md
      review-queue/
        SKILL.md
        README.md
      digest-composer/
        SKILL.md
        README.md
      telegram-delivery/
        SKILL.md
        README.md
      feedback-sync/
        SKILL.md
        README.md
      memory-sync/
        SKILL.md
        README.md

    automation/
      README.md
      cron/
        README.md
        morning-digest.md
        retry-recovery.md
        maintenance.md
      hooks/
        README.md
        hook-policy.md

  docs/
    README.md
    product/
    architecture/
    operations/
```

## Required Top-level Files

### `README.md`

Required. This is the main OpenClaw-facing install entrypoint.

Must include:

- project summary
- what OpenClaw should discover
- repository map
- install order
- environment requirements
- validation entrypoint

### `LICENSE`

Required if the repo is meant to be shared or reused.

### `.gitignore`

Required to prevent local runtime artifacts, secrets, and generated files from polluting the repo.

## Required Planning Files

These files are already the planning source of truth and should stay versioned in-repo.

- `01-design-v1.2.md`
- `02-implementation-plan.md`
- `03-test-plan.md`
- `04-openclaw-patterns-evaluation.md`
- `05-api-schema-contracts.md`
- `06-openclaw-runtime-blueprint.md`
- `07-repo-bootstrap-contract.md`
- `08-repo-file-skeleton.md`

## Required Bootstrap Files

### `bootstrap/README.md`

Short bootstrap index.

Should answer:

- where to start
- what each bootstrap doc is for

### `bootstrap/install.md`

Main installation walkthrough.

Should answer:

- how OpenClaw should interpret this repo
- what must be linked or loaded first
- which secrets must be supplied

### `bootstrap/validate.md`

Smoke test and acceptance path.

Should answer:

- how to confirm the agent loads
- how to confirm skills are visible
- how to confirm Telegram can send
- how to confirm one dry-run digest works

### `bootstrap/env.example`

Non-secret environment contract.

Should include placeholders for:

- Telegram token variable names
- target chat/topic identifiers
- optional feed-related config

### `bootstrap/repo-map.md`

Human-readable path map.

Useful because OpenClaw and humans should both be able to find the runtime assets quickly.

## Required OpenClaw Runtime Files

### `openclaw/README.md`

Explains what the `openclaw/` subtree contains and how it maps to runtime behavior.

### `openclaw/agents/editorial/AGENT.md`

Primary agent identity file.

Should include:

- mission
- scope boundaries
- linked standing orders
- linked memory conventions

### `openclaw/agents/editorial/README.md`

Operator-oriented explanation of the editorial agent.

### `openclaw/agents/editorial/standing-orders/*.md`

Minimum set:

- `daily-editorial.md`
- `memory-policy.md`
- `escalation-policy.md`

These should encode durable instructions, not transient state.

### `openclaw/agents/editorial/memory/README.md`

Explains what should be written into memory and what should not.

## Required Skill Files

Each required Phase 1 skill should have:

- `SKILL.md`
- `README.md`

### `SKILL.md`

Should define:

- the skill's job
- its boundaries
- expected inputs
- expected outputs
- failure behavior

### `README.md`

Should explain:

- how the skill fits into the pipeline
- what other skills it interacts with
- what implementation files later belong beside it

## Required Automation Files

### `openclaw/automation/README.md`

High-level automation overview.

### `openclaw/automation/cron/README.md`

Schedule map.

### `openclaw/automation/cron/morning-digest.md`

Should define:

- trigger intent
- expected workflow
- success criteria

### `openclaw/automation/cron/retry-recovery.md`

Should define delivery retry rules.

### `openclaw/automation/cron/maintenance.md`

Should define maintenance and health summary intent.

### `openclaw/automation/hooks/README.md`

Hook overview.

### `openclaw/automation/hooks/hook-policy.md`

Must clarify that hooks are non-authoritative and cannot become a second state machine.

## Optional But Recommended Files

### `docs/product/`

Longer-form product rationale and user-facing concepts.

### `docs/architecture/`

Generated diagrams and deeper technical notes later.

### `docs/operations/`

Runbooks, incident notes, and operator guidance later.

## Starter File Priority

If the macOS implementation session wants the minimum useful repo shell first, create files in this order:

1. `README.md`
2. `bootstrap/install.md`
3. `bootstrap/validate.md`
4. `openclaw/README.md`
5. `openclaw/agents/editorial/AGENT.md`
6. `openclaw/agents/editorial/standing-orders/daily-editorial.md`
7. `openclaw/skills/*/SKILL.md`
8. `openclaw/automation/cron/morning-digest.md`
9. `openclaw/automation/hooks/hook-policy.md`

## Template-vs-Implementation Rule

Many Phase 1 files will start as declarative or explanatory files before the real runtime implementation exists.

That is acceptable as long as:

- the file path is stable
- the responsibility is clear
- later implementation can fill the file instead of moving it

## Packaging Acceptance Checklist

- repo tree makes `openclaw/` obvious at first glance
- the editorial agent is discoverable without searching chat history
- required skills each have a dedicated stable path
- cron and hook intent are visible from the repo
- bootstrap docs explain install and validate flows
- planning docs and runtime layout do not contradict each other

## Recommended Next Step

The next document after this should be:

- `09-root-readme-draft.md`

That file should draft the actual repository root README content so the install story is not left implicit.
