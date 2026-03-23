# review-queue

## Job

Build consistent `ReviewQueueSnapshot` views for Telegram and any future thin
inspection surface.

## Expected Inputs

- current `StoryPack` projections
- feedback-derived status changes

## Expected Outputs

- version-consistent `ReviewQueueSnapshot` records
- ordered review state for digest composition and action handling

## Boundaries

- queue progression must respect snapshot semantics
- do not send transport messages here
- do not accept stale writes here

## Failure Behavior

- surface inconsistent queue build errors visibly
- never mix items from incompatible snapshot versions
