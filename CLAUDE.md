# CLAUDE.md — local context for contributors

> This file is auto-loaded when a Claude Code session opens in this repo. It's intentionally short; the full standards live in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this repo is

A curated reference for **agent workspaces**, with a worked example built in Claude Code: a redacted snapshot of one person's working setup, published so others can fork the patterns. The Claude-Code file conventions (`CLAUDE.md`, `.claude/skills/`, MCP config) are the substrate; the architectural patterns generalise to any agent system.

Maintained solo and best-effort. [Issues](https://github.com/jimy-r/agent-workspace-architecture/issues) for corrections and concrete proposals, PRs for changes. See [PATTERNS.md](PATTERNS.md) for the reasoning behind the architecture.

## Working principles

- **Always branch.** Never commit to `main` directly. Branch protection blocks force-pushes and deletions and requires the `redaction` check to pass on PRs (admins can still self-merge).
- **One focused change per PR.**
- **[Conventional Commits](https://www.conventionalcommits.org/).** `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
- **Include a `Co-Authored-By:` trailer** for Claude-assisted commits.
- **Run the redaction check before every commit** (see below).

## Privacy — hard rule

Every commit must be safe for a public audience. Before `git add`, scrub every changed file for:

- **Personal identifiers.** Real names, emails, usernames tied to identity, home or workplace locations.
- **Business / product specifics.** Company names, product names, customer details tied to a real entity.
- **Credentials, tokens, API keys.** Ever, even as placeholders.
- **Health, financial, or legal data.** Ever.
- **Absolute paths** that reveal a user's machine layout.

**Use generic placeholders:** `<workspace>`, `<home>`, `<project>`, `<workspace-id>`, "the user", "a commercial password manager", "`<PaaS>`", "`<cloud-provider>`".

When in doubt, generalise. If Claude drafts content with identifying info, stop and rewrite before staging.

## Follow the existing shape

- **Roles.** Schema in [`samples/roles/_template.md`](samples/roles/_template.md) (Identity / Directives / Constraints / Method / Output / Red Flags / Rationalization Table).
- **Skills.** CSO-style description plus procedure. See [`samples/.claude/skills/orient/SKILL.md`](samples/.claude/skills/orient/SKILL.md).
- **Project context files.** See [`samples/CONTEXT.md.example`](samples/CONTEXT.md.example).
- **Keep entity facts out of roles.** Roles are pure; entity facts live in CONTEXT.md.

## Scope boundaries

Some files need Discussion/Issue agreement before a PR; see the Scope boundaries section in [CONTRIBUTING.md](CONTRIBUTING.md). Everything else is fair game for direct PRs.

## Before you push

1. Run the redaction grep.
2. `git diff`, and eyeball every changed line.
3. Conventional commit message.
4. Push your branch; open a PR using the template.
5. Merge once the `redaction` check passes:
   `gh pr merge --squash --delete-branch`.
   `main` is protected: the `redaction` check must go green before a PR merges, and force-pushes and deletions are blocked. Add `--auto` to queue the merge for when the check passes (if auto-merge is enabled). Contributor PRs follow the same command once the maintainer has reviewed and approved them.
6. Open the merged commit on GitHub and verify Mermaid / markdown rendered correctly. Any leak or render bug after merge means a follow-up commit; amending never fully erases a public mistake.

## Tone

Terse, structural, opinionated. No performative politeness. Disagreement welcome; keep it focused on the work.

---

*Last verified against the repo structure on **2026-05-30**.*
