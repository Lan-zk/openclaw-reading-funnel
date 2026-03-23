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
