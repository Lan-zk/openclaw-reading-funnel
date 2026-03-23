# feed-ingest

## Job

Fetch enabled feeds and emit raw candidate items plus per-source run status.

## Expected Inputs

- enabled feed source records
- fetch window or cursor state when later implemented

## Expected Outputs

- raw candidate items ready for canonical extraction
- source run success or failure records

## Boundaries

- fetch feed-based inputs only
- do not normalize or merge content here
- do not hide per-source failures

## Failure Behavior

- mark source run failure as `FEED_FETCH_FAILED`
- continue remaining sources when safe
- keep failures visible in the operational summary
