# Memory Policy

- OpenClaw memory is for durable editorial context, not canonical business state.
- Only write approved durable outcomes into memory.
- Do not write noisy clickstream, transient queue state, or low-confidence partials into memory.
- Memory files should point back conceptually to canonical application state.
