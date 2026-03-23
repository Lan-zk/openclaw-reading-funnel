# storypack-builder

## Job

Create, merge, revise, and version `StoryPack` state from canonical items.

## Expected Inputs

- normalized canonical items and evidence records
- current `StoryPack` state

## Expected Outputs

- new or revised versioned `StoryPack` objects
- explicit escalation when merge certainty is too low

## Boundaries

- canonical StoryPack ownership lives here
- do not send digests or write memory here
- do not silently merge ambiguous clusters

## Failure Behavior

- assign `STORYPACK_NEEDS_MANUAL_SPLIT` when false merge risk is too high
- preserve prior canonical truth on unsafe merge attempts
