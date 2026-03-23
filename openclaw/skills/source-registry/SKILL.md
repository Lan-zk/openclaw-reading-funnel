# source-registry

## Job

Own feed source registration, validation, enable/disable state, and duplicate
prevention for Phase 1.

## Expected Inputs

- source create or disable requests
- current source registry state

## Expected Outputs

- validated feed-based source records
- safe rejection for invalid or duplicate source changes

## Boundaries

- Phase 1 accepts feed-based sources only
- do not fetch content here
- do not normalize content or build StoryPacks here

## Failure Behavior

- reject invalid config as `INVALID_SOURCE_CONFIG`
- reject duplicate active source as `DUPLICATE_SOURCE`
- disabling a source must fail safe for active runs
