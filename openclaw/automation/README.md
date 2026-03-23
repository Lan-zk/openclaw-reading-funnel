# Automation

This directory contains automation notes or configs for cron jobs and hooks.

The intent is to make scheduled behavior and hook behavior discoverable from
the repository.

## Phase 1 Automation Model

- cron drives the morning digest, retry recovery, and maintenance loops
- hooks stay lightweight and non-authoritative
- exact RRULEs are deferred to macOS setup, but job intent is fixed here

## Read Next

- `cron/README.md`
- `hooks/README.md`
