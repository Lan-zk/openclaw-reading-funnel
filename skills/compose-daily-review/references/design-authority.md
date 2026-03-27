# Design Authority

Use this skill's implementation as a workflow shell only.

Authority order for behavior:

1. `docs/workflows/compose-daily-review/reading-funnel-compose-daily-review-atomic-design.md`
2. `docs/workflows/compose-daily-review/reading-funnel-compose-daily-review-object-contracts.md`
3. `docs/workflows/compose-daily-review/reading-funnel-compose-daily-review-orchestration-rules.md`
4. `docs/workflows/compose-daily-review/reading-funnel-compose-daily-review-evaluation-rules.md`
5. `docs/global/reading-funnel-skills-development-spec.md`

When editing this skill:

- Keep `SKILL.md` lean and workflow-oriented.
- Keep implementation under `scripts/compose_daily_review/`.
- Keep detailed design knowledge in the authoritative docs above, not duplicated into `SKILL.md`.
- Do not expand this skill into `ingest-normalize`, `digest-candidates`, `curate-retain`, or other workflows.
- Keep JSON artifacts under `artifacts/compose-daily-review/<run_id>/`.
