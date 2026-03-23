# Daily Editorial Standing Orders

## Mission

Produce a high-signal daily editorial loop using deterministic runtime steps.

## Default Run Order

1. `source-registry`
2. `feed-ingest`
3. `content-extract`
4. `storypack-builder`
5. `review-queue`
6. `digest-composer`
7. `telegram-delivery`
8. `feedback-sync`
9. `memory-sync`

## Non-negotiable Rules

- Prefer deterministic workflow over broad autonomous planning.
- Use feed-based ingestion as the default Phase 1 input path.
- Treat Telegram as the first delivery and approval surface.
- Keep `StoryPack`, `FeedbackEvent`, `DeliveryArtifact`, and
  `ReviewQueueSnapshot` in explicit application state.
- Every mutating review action must carry `story_pack_id`,
  `expected_version`, `snapshot_id`, and `idempotency_key`.
- Delivery retries must reuse the same built artifact rather than rebuilding
  different content.
- Use `quiet_but_useful` only as an explicit artifact type, not as a silent
  null fallback.
- Continue safe partial progress on per-source ingest failure while keeping
  failures visible in ops summaries.

## Escalate Instead Of Guessing

- low-confidence or contradictory StoryPack merge
- repeated stale-version conflicts
- repeated delivery anomalies
- repeated memory sync failures
