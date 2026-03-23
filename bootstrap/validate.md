# Validate

Use this checklist after bootstrap to confirm the repo is discoverable and the Phase 1 runtime is coherent.

## Validation Goals

Confirm that:

1. the editorial agent is discoverable
2. required skills are discoverable
3. automation layout is readable
4. memory conventions are visible
5. a dry-run digest flow can be simulated safely

## Validation Checklist

### Repository discovery

- root `README.md` is present
- `openclaw/` subtree is present
- `bootstrap/` subtree is present
- planning pack is present

### Agent discovery

- `openclaw/agents/editorial/AGENT.md` exists
- standing orders exist
- memory policy exists

### Skill discovery

- each required Phase 1 skill has its own stable directory
- each required skill has `SKILL.md`

### Automation discovery

- cron docs exist
- hook policy exists

### Runtime safety

- source-of-truth rule is documented
- Telegram-first review rule is documented
- memory write-through policy is documented

## Dry-run validation

```text
Feed source discovered
  -> ingest skill discoverable
  -> StoryPack build path discoverable
  -> digest composer discoverable
  -> Telegram delivery path discoverable
  -> feedback sync path discoverable
```

## Success Criteria

Validation passes when a new operator can understand:

- where to start
- where the main agent lives
- where the skills live
- where Telegram delivery is defined
- where to continue into implementation
