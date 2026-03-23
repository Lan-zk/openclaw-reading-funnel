# memory-sync

## Job

Mirror approved durable StoryPack outcomes into OpenClaw memory without making
memory canonical.

## Expected Inputs

- eligible `StoryPack` version
- requested memory write kind

## Expected Outputs

- memory markdown write or update
- `MemoryWriteRecord`

## Boundaries

- only approved durable outcomes are eligible
- writes are additive mirrors of app state, not replacements for it
- same write kind per StoryPack version must be idempotent

## Failure Behavior

- mark `MEMORY_SYNC_FAILED` without rolling back canonical StoryPack state
- keep failed memory writes visible for independent retry
