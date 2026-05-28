# Canary C1 — credential pattern outside .env

**Audit canary fixture (R4). Do not action.** This file deliberately contains
a fake credential-shaped string so the audit's Phase 2.6 credential grep
keeps catching `sk-ant-api-*` patterns outside `.env`. If the audit stops
reporting `CANARY-CONFIRMED: C1`, the credential grep has regressed.

Expected pattern (the audit must find this on every run):

```
ANTHROPIC_API_KEY=sk-ant-api-CANARY-FAKE-NEVER-USE-0123456789abcdef0123456789abcdef
```

The string above is **not a real credential**. It contains the literal token
`CANARY-FAKE-NEVER-USE` precisely so a human glancing at a Phase 2.6 finding
can distinguish it from a real exposure. The audit reports this under
`CANARY-CONFIRMED` in the Phase 0 verification block, not under Security.

See `tests/audit_canaries/canary.json` for the full manifest.
