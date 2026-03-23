# Cron Jobs

This directory describes the scheduled jobs used by the Phase 1 editorial
runtime.

## Planned Jobs

- `morning-digest.md`
  - once per day during the user's preferred morning window
- `retry-recovery.md`
  - hourly during waking hours
- `maintenance.md`
  - once per day after the digest cycle

Exact RRULEs are chosen during macOS setup. The workflow boundaries documented
here are runtime constraints, not optional suggestions.
