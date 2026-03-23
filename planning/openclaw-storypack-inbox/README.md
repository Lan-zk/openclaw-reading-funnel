# OpenClaw StoryPack Inbox Planning Pack

Generated: 2026-03-23  
Status: Draft  
Purpose: handoff-ready planning package for later implementation on macOS

## What This Pack Is

This folder is the persisted planning package for the OpenClaw-based information funnel project.

It is designed to prevent scope drift during later implementation by locking:

- product scope
- runtime boundaries
- state ownership
- OpenClaw-native operating model
- implementation order
- test bar

## Document Map

- [01-design-v1.2.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\01-design-v1.2.md)
  - main design doc
  - now updated to the OpenClaw-native Phase 1.3 model
- [02-implementation-plan.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\02-implementation-plan.md)
  - step-by-step implementation order for macOS development
- [03-test-plan.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\03-test-plan.md)
  - verification plan synced to the OpenClaw-native runtime
- [04-openclaw-patterns-evaluation.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\04-openclaw-patterns-evaluation.md)
  - assessment against OpenClaw docs/source, ADP, and Google pattern guidance
- [05-api-schema-contracts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\05-api-schema-contracts.md)
  - implementation-facing schema and service contract draft
- [06-openclaw-runtime-blueprint.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\06-openclaw-runtime-blueprint.md)
  - concrete OpenClaw runtime layout for agent, skills, cron, hooks, Telegram, and memory
- [07-repo-bootstrap-contract.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\07-repo-bootstrap-contract.md)
  - repository packaging contract so OpenClaw can bootstrap from the GitHub repo itself
- [08-repo-file-skeleton.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\08-repo-file-skeleton.md)
  - exact repository tree and starter file inventory for the installable repo
- [09-root-readme-draft.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\09-root-readme-draft.md)
  - draft of the actual repository root README for OpenClaw and human bootstrap
- [10-bootstrap-doc-drafts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\10-bootstrap-doc-drafts.md)
  - draft contents for `bootstrap/install.md`, `validate.md`, `env.example`, and `repo-map.md`
- [11-openclaw-runtime-file-drafts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\11-openclaw-runtime-file-drafts.md)
  - draft contents for the first runtime-facing files under `openclaw/`
- [12-macos-build-sequence.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\12-macos-build-sequence.md)
  - recommended order of work for the actual macOS implementation session

## Recommended Reading Order

1. [01-design-v1.2.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\01-design-v1.2.md)
2. [04-openclaw-patterns-evaluation.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\04-openclaw-patterns-evaluation.md)
3. [06-openclaw-runtime-blueprint.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\06-openclaw-runtime-blueprint.md)
4. [07-repo-bootstrap-contract.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\07-repo-bootstrap-contract.md)
5. [08-repo-file-skeleton.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\08-repo-file-skeleton.md)
6. [09-root-readme-draft.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\09-root-readme-draft.md)
7. [10-bootstrap-doc-drafts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\10-bootstrap-doc-drafts.md)
8. [11-openclaw-runtime-file-drafts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\11-openclaw-runtime-file-drafts.md)
9. [05-api-schema-contracts.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\05-api-schema-contracts.md)
10. [12-macos-build-sequence.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\12-macos-build-sequence.md)
11. [02-implementation-plan.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\02-implementation-plan.md)
12. [03-test-plan.md](E:\File\self\github\agents\planning\openclaw-storypack-inbox\03-test-plan.md)

## Core Decisions Locked In

1. `StoryPack` is a versioned entity.
2. `FeedbackEvent` is the source of truth and projections are derived.
3. `DeliveryArtifact` has a real idempotency and retry contract.
4. Review queue semantics use explicit snapshots.
5. OpenClaw is the orchestration/runtime layer, not the business database.
6. Phase 1 defaults to `one editorial agent + narrow skills`, not many agents.
7. `Telegram` is the first delivery and approval surface.
8. `Canvas / A2UI` is the first custom surface to consider before a bespoke web app.
9. OpenClaw memory uses selective write-through; app state remains canonical.
10. The repository itself must be packaged as an OpenClaw-installable bundle.

## What Phase 1 Is

Phase 1 is:

- feed-based ingestion
- StoryPack building
- queue creation
- Telegram digest delivery
- Telegram inline feedback
- selective memory write-through
- repo-structured bootstrap for OpenClaw installation

It is not:

- browser-heavy crawling by default
- card/article generation
- full social publishing
- a many-agent playground
- a full standalone admin SaaS

## Planning Pack Status

This pack now covers:

- product scope
- OpenClaw-native runtime design
- bootstrap packaging contract
- repository skeleton
- root README draft
- bootstrap doc drafts
- runtime file drafts
- API/schema contracts
- implementation order
- test bar

The next session does not need more planning by default. It should start materializing the repository shape itself.
