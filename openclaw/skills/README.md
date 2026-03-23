# Skills

This directory contains the repo-bundled Phase 1 skills for the StoryPack Inbox
runtime.

## Required Phase 1 Skill Inventory

1. `source-registry`
2. `feed-ingest`
3. `content-extract`
4. `storypack-builder`
5. `review-queue`
6. `digest-composer`
7. `telegram-delivery`
8. `feedback-sync`
9. `memory-sync`

## Skill Contract Rule

Each skill directory must include:

- `SKILL.md`
  - job, boundaries, expected inputs, expected outputs, and failure behavior
- `README.md`
  - pipeline role, adjacent skills, and what later implementation files belong
    beside the skill

## Pipeline Shape

The editorial agent should be able to discover the whole Phase 1 runtime by
reading this directory plus `../agents/editorial/` and `../automation/`.
