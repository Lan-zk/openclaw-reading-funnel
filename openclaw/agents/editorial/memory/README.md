# Editorial Memory

This directory is for mirrored durable editorial context.

It must not become the canonical storage for StoryPack truth.

## Intended Layout

- `editorial/preferences.md`
  - stable preferences learned from approved outcomes
- `editorial/approved-storypacks/`
  - mirrored narrative records for approved durable StoryPack outcomes

## Hard Rule

A memory file is a human-readable mirror of selected conclusions. It is never
the authoritative state object for `StoryPack`, `FeedbackEvent`,
`DeliveryArtifact`, or `ReviewQueueSnapshot`.
