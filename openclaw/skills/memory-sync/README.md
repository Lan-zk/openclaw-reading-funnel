# memory-sync

Owns selective write-through of approved durable outcomes into OpenClaw memory.

## Pipeline Position

- downstream of approved review outcomes
- downstream of canonical StoryPack state changes

## Interacts With

- `MemoryWriteRecord`
- editorial memory conventions
- approved outcome and preference sync rules

## Later Implementation Files

- memory serializer
- write record helper
- durable preference update helpers
