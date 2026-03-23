# content-extract

## Job

Convert raw feed items into canonical evidence records suitable for StoryPack
ownership.

## Expected Inputs

- raw candidate items from `feed-ingest`

## Expected Outputs

- normalized canonical items
- `EvidenceItem` records with extraction metadata and confidence

## Boundaries

- canonicalize and normalize content only
- do not decide StoryPack ownership or queue order here
- malformed content should degrade visibly rather than disappear

## Failure Behavior

- return `NORMALIZATION_FAILED` for extraction failures
- preserve a visible failure or degraded record for ops review
