# Editorial Agent

This is the main runtime identity for Phase 1.

## What Lives Here

- `AGENT.md` defines the agent mission, boundaries, and runtime role
- `standing-orders/` stores durable editorial policy that must survive across
  runs
- `memory/` documents what may be mirrored into OpenClaw memory and what must
  stay in canonical application state

## Phase 1 Default

The editorial agent remains the default orchestrator unless a later phase proves
that separate auth, workspace, or tool isolation is necessary for a new agent.

## Runtime Contract

This agent owns orchestration. It does not own business truth by itself. The
canonical lifecycle still lives in versioned application objects such as
`StoryPack`, `FeedbackEvent`, `DeliveryArtifact`, and `ReviewQueueSnapshot`.
