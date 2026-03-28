# Design Authority

Use this skill's implementation as a workflow shell only.

Authority order for behavior:

1. `docs/workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-atomic-design.md`
2. `docs/workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-object-contracts.md`
3. `docs/workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-orchestration-rules.md`
4. `docs/workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-evaluation-rules.md`
5. `docs/workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-signal-and-writability-rules.md`
6. `docs/global/reading-funnel-skills-development-spec.md`

When editing this skill:

- Keep `SKILL.md` lean and workflow-oriented.
- Keep implementation under `scripts/generate_long_cycle_assets/`.
- Keep detailed design knowledge in the authoritative docs above, not duplicated into `SKILL.md`.
- Do not expand this skill into `ingest-normalize`, `digest-candidates`, `compose-daily-review`, or `curate-retain`.
- Keep JSON artifacts under `artifacts/generate-long-cycle-assets/<run_id>/`.
