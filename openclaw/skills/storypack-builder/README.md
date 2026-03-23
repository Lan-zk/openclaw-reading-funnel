# storypack-builder

Owns StoryPack creation, merge, update, and split escalation.

## Pipeline Position

- downstream of `content-extract`
- upstream of `review-queue`

## Interacts With

- `StoryPack` schema and versioning rules
- merge confidence scoring
- manual split escalation paths

## Later Implementation Files

- StoryPack repository or store helpers
- merge policy and scoring helpers
- revision reason or provenance helpers
