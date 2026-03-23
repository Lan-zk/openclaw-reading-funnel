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
