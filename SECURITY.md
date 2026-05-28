# Security policy

This repository contains **only documentation and illustrative sample scaffolds**. It ships no executable code that runs against user systems, no dependencies that end users install, no service this repo operates.

That narrows the threat surface to three categories:

## What to report, and where

### 1. Privacy leaks in committed content

If you spot personal identifiers, credentials, tokens, business specifics, or other content that shouldn't be in a public repo — **open a public Issue using the [Moderation report template](https://github.com/jimy-r/agent-workspace-architecture/issues/new?template=moderation_report.yml)** with category "Privacy leak." Public visibility is appropriate here because the content is already public on GitHub; the faster we excise it, the better.

Do **not** include the leaked content in the report. Link to the file and line.

### 2. Vulnerabilities in the GitHub Actions workflows

The repo runs workflows (`link-check`, `stale`, `validate-samples`, `dependabot`, `labeler`, `lock-closed`) under the repo's `GITHUB_TOKEN`. If you spot an injection risk, permission escalation path, or supply-chain concern in any of these:

- Use **GitHub's [private security advisories](https://github.com/jimy-r/agent-workspace-architecture/security/advisories/new)** — not a public Issue.
- Maintainer will triage and coordinate a fix before public disclosure.

### 3. Patterns in the docs that would weaken a reader's workspace security

The `META_ARCHITECTURE.md`, `ADOPTION.md`, and `samples/` files describe patterns others may adopt in their own workspaces. If a documented pattern would actively harm a reader's security posture (e.g. suggests an unsafe hook config, demonstrates leaking credentials, etc.), flag it via **private security advisory** so the fix lands before propagation, not via a public Issue.

## Out of scope

- Vulnerabilities in **Claude Code itself** — report to [anthropics/claude-code](https://github.com/anthropics/claude-code) under their security policy.
- Vulnerabilities in **third-party tools** this repo references (e.g. `restic`, `lychee`, `prettier`) — report upstream.
- General Claude Code usage questions — see [SUPPORT.md](SUPPORT.md).

## Maintainer response

Private security advisories get a first response within a week. A published fix or disclosure timeline follows once the scope is understood. If you don't hear back in two weeks, ping via a Discussion (without revealing the vulnerability).

---

*Last verified against the repo structure on **2026-04-19**.*
