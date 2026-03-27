# Design Authority

Use this skill's implementation as a workflow shell only.

Authority order for behavior:

1. `docs/workflows/ingest-normalize/reading-funnel-ingest-normalize-atomic-design.md`
2. `docs/workflows/ingest-normalize/reading-funnel-ingest-normalize-object-contracts.md`
3. `docs/workflows/ingest-normalize/reading-funnel-ingest-normalize-orchestration-rules.md`
4. `docs/workflows/ingest-normalize/reading-funnel-ingest-normalize-evaluation-rules.md`
5. `docs/workflows/ingest-normalize/reading-funnel-ingest-normalize-adapter-and-normalization-rules.md`

When editing this skill:

- Keep `SKILL.md` lean and workflow-oriented.
- Keep implementation under `scripts/ingest_normalize/`.
- Keep detailed design knowledge in the authoritative docs above, not duplicated into `SKILL.md`.
- Do not expand this skill into `digest-candidates` or other workflows.
- Keep JSON artifacts under `artifacts/ingest-normalize/<run_id>/`.
