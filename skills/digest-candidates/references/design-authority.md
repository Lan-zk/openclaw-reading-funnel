# Design Authority

Use this skill's implementation as a workflow shell only.

Authority order for behavior:

1. `docs/workflows/digest-candidates/reading-funnel-digest-candidates-atomic-design.md`
2. `docs/workflows/digest-candidates/reading-funnel-digest-candidates-object-contracts.md`
3. `docs/workflows/digest-candidates/reading-funnel-digest-candidates-orchestration-rules.md`
4. `docs/workflows/digest-candidates/reading-funnel-digest-candidates-evaluation-rules.md`
5. `docs/workflows/digest-candidates/reading-funnel-digest-candidates-heuristics-and-scoring-rules.md`
6. `docs/global/reading-funnel-skills-development-spec.md`

When editing this skill:

- Keep `SKILL.md` lean and workflow-oriented.
- Keep implementation under `scripts/digest_candidates/`.
- Keep detailed design knowledge in the authoritative docs above, not duplicated into `SKILL.md`.
- Do not expand this skill into `ingest-normalize`, `compose-daily-review`, or other workflows.
- Keep JSON artifacts under `artifacts/digest-candidates/<run_id>/`.
