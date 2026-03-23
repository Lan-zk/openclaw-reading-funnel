# Memory Policy

## Memory Is For

- durable editorial preferences
- approved summaries worth remembering
- stable thesis fragments such as `why_it_matters_today` or
  `one_line_thesis`
- mirrored narrative records of approved outcomes

## Memory Is Not For

- canonical `StoryPack` lifecycle truth
- raw queue position or transient review state
- noisy clickstream and low-confidence partials
- transport-level Telegram metadata

## Write-through Rules

- Only approved durable outcomes are eligible for memory sync.
- Each write should reference the source `story_pack_id` and version.
- The same write kind for the same StoryPack version must be idempotent.
- Memory sync failure must not roll back canonical application state.
- Memory files should clearly indicate that application state remains the source
  of truth.
