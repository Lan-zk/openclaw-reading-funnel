# Design Authority

Use this skill's implementation as a workflow shell only.

Authority order for behavior:

1. `docs/workflows/curate-retain/reading-funnel-curate-retain-atomic-design.md`
2. `docs/workflows/curate-retain/reading-funnel-curate-retain-object-contracts.md`
3. `docs/workflows/curate-retain/reading-funnel-curate-retain-orchestration-rules.md`
4. `docs/workflows/curate-retain/reading-funnel-curate-retain-evaluation-rules.md`
5. `docs/workflows/curate-retain/reading-funnel-curate-retain-rules-and-taxonomy.md`
6. `docs/global/reading-funnel-skills-development-spec.md`

When editing this skill:

- Keep `SKILL.md` lean and workflow-oriented.
- Keep implementation under `scripts/curate_retain/`.
- Keep detailed design knowledge in the authoritative docs above, not duplicated into `SKILL.md`.
- Do not expand this skill into `digest-candidates`, `compose-daily-review`, or other workflows.
- Keep JSON artifacts under `artifacts/curate-retain/<run_id>/`.
