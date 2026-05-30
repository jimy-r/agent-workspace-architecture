<!--
Thanks for contributing.

PR title format — Conventional Commits, lowercase description, present tense:

  ✅  feat: add developmental-editor role with pressure-test notes
  ✅  fix: correct Mermaid anchor in META_ARCHITECTURE §5
  ✅  docs: clarify redaction rules in CONTRIBUTING
  ✅  chore: pin actions/checkout to v4.1.7

  ❌  Update CONTRIBUTING
  ❌  [WIP] new role
  ❌  fixed a bug

Types: feat | fix | docs | refactor | chore
See CONTRIBUTING.md § Commit conventions for the full list.
-->

## What changed

<!-- One-paragraph description of the change. -->

## Why

<!--
Make it specific.

  ✅  Solves a problem I hit while adapting the orient skill to my own workspace.
  ✅  Corrects a broken link flagged by the weekly link-check cron.
  ✅  Adds a role I've used across three projects; schema matches the template.

  ❌  "Because it's better"            (vague)
  ❌  "Adds a useful role"              (useful to whom? what problem?)
  ❌  "Cleanup"                         (scope unclear, will be bounced)
-->

## Type

- [ ] Bug fix / typo / broken link / clarity improvement
- [ ] New component (role / skill / hook / scheduled task / MCP pattern)
- [ ] Workflow improvement to an existing pattern
- [ ] Doc reorganisation
- [ ] Other

## Privacy checklist

- [ ] No personal identifiers (names, emails, usernames tied to identity)
- [ ] No business / product / infrastructure specifics tied to a real entity
- [ ] No credentials, tokens, API keys, or paths that reveal a user's machine layout
- [ ] No health, financial, or legal data
- [ ] Generic placeholders used where appropriate (`<workspace>`, `<home>`, "the user", etc.)

## Scope boundaries

- [ ] I have **not** touched any file listed in [CONTRIBUTING.md § Scope boundaries](../CONTRIBUTING.md#scope-boundaries), **or** I have linked the Discussion / Issue that pre-agreed the change below.

## Related

<!-- Link the Issue or Discussion this comes from, if any. -->

---

<!--
Before pushing:
  1. Run the redaction grep on changed files.
  2. git diff — eyeball every changed line.
  3. One focused change per PR; split unrelated fixes into separate PRs.
  4. Get explicit human approval if this was drafted by an AI agent.
  5. Verify Mermaid / heavy markdown renders correctly on GitHub.
-->
