# API And Schema Contract Draft: OpenClaw StoryPack Inbox Phase 1.3

Generated: 2026-03-23  
Status: Draft  
Purpose: convert the locked planning decisions into implementation-facing contracts for later macOS development

## Contract Philosophy

These contracts are designed around five rules:

1. application state is canonical
2. OpenClaw memory is selective write-through context
3. StoryPack writes are versioned
4. delivery is idempotent
5. Telegram actions and any future UI must share the same state model

## Core Entities

## StoryPack

```yaml
StoryPack:
  story_pack_id: string
  version: integer
  title: string
  summary: string
  angle: string | null
  canonical_topic: string | null
  why_it_matters_today: string | null
  one_line_thesis: string | null
  publish_intent: enum[none, candidate, approved_for_prep]
  status_projection: enum[queued, approved, rejected, snoozed, delivered]
  importance_score: number
  novelty_score: number
  confidence_score: number
  public_interest_score: number
  maturity_score: number
  source_count: integer
  evidence_items: EvidenceItem[]
  canonical_item_ids: string[]
  created_at: datetime
  updated_at: datetime
  last_revision_reason: string | null
```

## EvidenceItem

```yaml
EvidenceItem:
  evidence_item_id: string
  canonical_item_id: string
  source_url: string
  source_title: string
  snippet: string | null
  extracted_at: datetime
  confidence: number
```

## FeedbackEvent

```yaml
FeedbackEvent:
  feedback_event_id: string
  story_pack_id: string
  story_pack_version: integer
  snapshot_id: string | null
  actor: enum[user, system]
  action: enum[
    approved,
    rejected,
    snoozed,
    marked_for_memory,
    marked_for_publish,
    clicked_from_digest
  ]
  payload: object
  idempotency_key: string
  created_at: datetime
```

## DeliveryArtifact

```yaml
DeliveryArtifact:
  delivery_artifact_id: string
  artifact_type: enum[daily_digest, quiet_but_useful]
  channel: enum[telegram]
  selection_hash: string
  content_hash: string
  idempotency_key: string
  build_attempt: integer
  send_attempt: integer
  delivery_status: enum[built, sending, delivered, failed, dead_letter]
  error_code: string | null
  cooldown_window_hours: integer | null
  source_story_pack_ids: string[]
  payload: object
  built_at: datetime
  delivered_at: datetime | null
```

## ReviewQueueSnapshot

```yaml
ReviewQueueSnapshot:
  snapshot_id: string
  generated_at: datetime
  queue_type: enum[daily_review]
  ordered_story_pack_ids: string[]
  total_count: integer
  remaining_count: integer
  current_story_pack_id: string | null
  selection_reason: string | null
```

## MemoryWriteRecord

```yaml
MemoryWriteRecord:
  memory_write_id: string
  story_pack_id: string
  story_pack_version: integer
  write_kind: enum[approved_summary, why_today, one_line_thesis, durable_preference]
  target_memory_path: string
  status: enum[pending, written, failed]
  written_at: datetime | null
  error_code: string | null
```

## Service Contracts

The implementation may be REST, RPC, internal service methods, or a mixed architecture. The important part is contract behavior, not transport branding.

## Source Registry

### Create source

```http
POST /sources
```

Request:

```json
{
  "type": "feed",
  "name": "OpenAI Blog",
  "feed_url": "https://example.com/feed.xml",
  "enabled": true
}
```

Behavior:

- rejects duplicate active sources
- validates feed format when possible
- stores only feed-based sources in Phase 1

### Disable source

```http
POST /sources/{source_id}/disable
```

Behavior:

- future ingest runs skip the source
- active runs must fail safely without corrupting state

## Queue And Review

### Get current review state

```http
GET /inbox/current
```

Response:

```json
{
  "snapshot_id": "snap_123",
  "current_item": {
    "story_pack_id": "sp_001",
    "version": 4
  },
  "next_up": [
    {
      "story_pack_id": "sp_002",
      "version": 2
    }
  ],
  "remaining_count": 5
}
```

Behavior:

- `current_item` and `next_up` must come from the same snapshot
- this contract must work for Telegram and future UI surfaces

### Submit review action

```http
POST /storypacks/{story_pack_id}/actions
```

Request:

```json
{
  "action": "approved",
  "expected_version": 4,
  "snapshot_id": "snap_123",
  "idempotency_key": "tg-msg-778-approve"
}
```

Success response:

```json
{
  "feedback_event_id": "fe_777",
  "story_pack_id": "sp_001",
  "accepted_version": 4,
  "new_status_projection": "approved"
}
```

Conflict response:

```json
{
  "error": "STORYPACK_VERSION_CONFLICT",
  "story_pack_id": "sp_001",
  "expected_version": 4,
  "current_version": 5,
  "latest_status_projection": "queued"
}
```

Behavior:

- writes are rejected on version mismatch
- duplicate idempotency keys are safe
- action creates one `FeedbackEvent`

## Delivery

### Build digest artifact

```http
POST /delivery/build
```

Request:

```json
{
  "artifact_type": "daily_digest",
  "snapshot_id": "snap_123"
}
```

Response:

```json
{
  "delivery_artifact_id": "da_111",
  "artifact_type": "daily_digest",
  "selection_hash": "sel_abc",
  "content_hash": "cnt_def",
  "delivery_status": "built"
}
```

Behavior:

- artifact build is deterministic for a given selection
- `quiet_but_useful` is a separate artifact type, not a null fallback

### Send artifact

```http
POST /delivery/{delivery_artifact_id}/send
```

Request:

```json
{
  "idempotency_key": "send-da_111-attempt1"
}
```

Behavior:

- retries must reuse the same artifact
- retries must not change content
- `send_attempt` increments, `selection_hash` and `content_hash` stay stable

## Memory Sync

### Write approved outcome to memory

```http
POST /memory-sync
```

Request:

```json
{
  "story_pack_id": "sp_001",
  "story_pack_version": 4,
  "write_kind": "approved_summary"
}
```

Behavior:

- only selected durable outcomes are eligible
- memory write failure must not roll back the canonical StoryPack state
- writes produce `MemoryWriteRecord`

## Event Projection Rules

These are not optional convenience logic. They are contract behavior.

### Status projection

```text
approved -> APPROVED
rejected -> REJECTED
snoozed -> SNOOZED
marked_for_publish -> publish_intent only
clicked_from_digest -> engagement only
```

### Queue projection

```text
approved/rejected/snoozed
  -> remove current item from active position
  -> decrement remaining count
  -> advance to next item in same snapshot when possible
```

### Learning projection

```text
marked_for_memory
marked_for_publish
clicked_from_digest
approved
  -> contribute to ranking inputs
```

## Idempotency Rules

### Review actions

- idempotency key scope: per action submission
- same key + same payload = safe replay
- same key + different payload = reject

### Delivery send

- idempotency key scope: per send attempt
- same artifact may have multiple send attempts
- repeated transport callbacks must not create duplicate durable state

### Memory write-through

- idempotency key scope: per write kind per StoryPack version
- same durable summary should not be written repeatedly as a new fact

## Error Codes

Recommended minimum set:

```text
STORYPACK_VERSION_CONFLICT
INVALID_SOURCE_CONFIG
DUPLICATE_SOURCE
FEED_FETCH_FAILED
NORMALIZATION_FAILED
STORYPACK_NEEDS_MANUAL_SPLIT
DELIVERY_BUILD_FAILED
DELIVERY_SEND_FAILED
DELIVERY_DEAD_LETTER
MEMORY_SYNC_FAILED
INVALID_TELEGRAM_ACTION
IDEMPOTENCY_CONFLICT
```

## Telegram Action Contract

Telegram is the first approval surface in Phase 1.

Each inline action payload should resolve to:

```json
{
  "story_pack_id": "sp_001",
  "expected_version": 4,
  "snapshot_id": "snap_123",
  "action": "approved",
  "idempotency_key": "telegram-callback-123"
}
```

Required behavior:

- invalid or stale action returns a safe user-visible failure
- duplicate callback is idempotent
- queue progression stays consistent with the same snapshot semantics

## Open Questions For Implementation

- whether these contracts should first live as internal service interfaces or external HTTP endpoints
- how to serialize memory write-through content on disk
- whether provenance needs a first-class table in Phase 1 or can piggyback on evidence records
- how much of the contract should be exposed directly to a future Canvas surface
