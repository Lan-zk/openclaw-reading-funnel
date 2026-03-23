# digest-composer

## Job

Build deterministic `DeliveryArtifact` payloads for `daily_digest` and
`quiet_but_useful`.

## Expected Inputs

- current review queue snapshot
- selected StoryPack records

## Expected Outputs

- built `DeliveryArtifact` records with stable `selection_hash` and
  `content_hash`

## Boundaries

- compose artifacts only
- do not send transport requests here
- `quiet_but_useful` is an explicit artifact type, not a hidden fallback

## Failure Behavior

- surface `DELIVERY_BUILD_FAILED`
- preserve enough context to retry or inspect without silently changing content
