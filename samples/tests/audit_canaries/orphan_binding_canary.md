---
name: orphan_binding_canary
description: This binding has no clear activation trigger
model: claude-sonnet-4-6
tools:
  - Read
---

# Orphan binding canary (C3)

**Audit canary fixture (R4). Do not action.** This file deliberately has a
description field that names *what* the binding does without specifying *when*
to invoke it. Phase 2.8 routing audit should flag it as `[missing-trigger]`.
If the audit stops reporting `CANARY-CONFIRMED: C3`, the missing-trigger
check has regressed.

This binding is NOT wired into any project's `.claude/agents/` folder, so
the routing system will never actually invoke it.

See `tests/audit_canaries/canary.json` for the full manifest.
