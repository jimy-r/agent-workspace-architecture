---
name: example-security
description: Security auditor for the Example Project. Invoke for security reviews, vulnerability assessments, or hardening audits specific to this project's codebase, credentials, and infrastructure.
tools: Read, Grep, Glob, Bash
model: claude-sonnet-4-6
---

@../../../roles/security-auditor.md

---

## Project context

@../../CONTEXT.md

---

## Binding notes

- **Read-only** — `tools:` excludes `Write` / `Edit`. The auditor produces findings; remediation is a separate write-enabled agent.
- **Cost choice** — Sonnet, not Opus. Upgrade the binding's `model:` line to Opus if a finding needs deep code-path analysis.
- **What the agent sees when invoked** — the canonical `security-auditor` role (identity, directives, constraints, rationalization table) plus this project's `CONTEXT.md` (stack, key paths, credential references). The binding itself is thin on purpose.
