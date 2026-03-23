# Maintenance

## Trigger Intent

Review runtime health after the main digest cycle.

## Workflow

1. summarize the previous run status
2. surface repeated stale-action conflicts
3. surface repeated merge anomalies
4. surface memory sync failures
5. emit a lightweight operational summary

## Success Criteria

- failures are visible without mutating canonical state
- repeated anomalies are easy to escalate
- the operator can see whether retry or manual review is required
