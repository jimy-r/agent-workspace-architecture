# Style guide

Writing and formatting conventions for this repo. Applied during review; reviewers link to a specific anchor here when correcting a PR.

## Voice

- **Terse, structural, opinionated.** Short sentences. Active voice.
- **No performative politeness.** "Thanks for contributing!" / "Great question!" don't belong in Issues or PRs; nor do their inverse. Critique ideas, not people.
- **First person singular** is fine when describing a pattern the author uses personally ("I run this nightly").
- **Second person ("you")** is fine in procedural / how-to docs (`ADOPTION.md` steps).
- **First person plural ("we").** Avoid it unless multiple maintainers are genuinely speaking collectively. Misleading in a single-maintainer repo.

## Privacy

See [CONTRIBUTING.md § Privacy](CONTRIBUTING.md#privacy--the-one-hard-rule) for the hard rule. Short version: never commit real names, addresses, business specifics, credentials, or machine-specific paths.

Use these placeholders:

| Use | Instead of |
|---|---|
| `<workspace>` | an actual working-directory path |
| `<home>` | an actual home-directory path |
| `<project>` | a named project folder |
| `<workspace-id>` | a hashed memory-path segment |
| "the user" / "the author" | a real first name |
| "a commercial password manager" | a vendor brand |
| `<PaaS>` / `<cloud-provider>` | a real service name |

**Author-attribution exception.** The maintainer's public byline **James Ross** and the practice site [jamesross.ai](https://jamesross.ai) may appear in author / attribution context. That's a deliberate public identity, not a leak. Never surface the maintainer's private or legal identity, and never use a third party's real name.

## Table type markers

When a table row describes a tool or component, mark it with one of:

- `[stock]` ships with Claude Code out of the box.
- `[plugin]` installs via a Claude Code plugin.
- `[local]` is a local external install (npm global, `uvx`, standalone binary).
- `[custom]` is written for this workspace.

Markers help readers budget adoption effort at a glance.

## Diagrams

- **Use Mermaid** (GitHub renders it natively). Don't commit ASCII diagrams except inside `<details>` as text fallback.
- Flowcharts for hierarchy, sequence diagrams for workflows, state diagrams where relevant.
- Keep node text short; use `<br/>` for line breaks inside a node label.
- After committing a diagram change, open the file on GitHub and verify rendering. Mermaid renders slightly differently in different editors.

## Freshness footer

Core docs (`README.md`, `CONTRIBUTING.md`, `META_ARCHITECTURE.md`, `PATTERNS.md`, `ADOPTION.md`, `WORKFLOW.md`, `CLAUDE.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, this file) end with:

```markdown
---

*Last verified against the repo structure on **YYYY-MM-DD**.*
```

Bump the date when you touch the file for a structural reason (not typos).

## Formatting

- **Headings.** ATX style (`#`), sentence case (not title case).
- **Lists.** Dash (`-`), not asterisk or plus.
- **Code fences.** Always specify a language (`mermaid`, `yaml`, `json`, etc.). Use `text` if nothing fits.
- **Tables.** GitHub-flavoured markdown. Don't over-pad columns; trailing-space alignment is noise.
- **Bold for emphasis**, italic for terms-on-first-use or soft emphasis. Don't mix.

## Commit messages

See [CONTRIBUTING.md § Commit conventions](CONTRIBUTING.md#commit-conventions). Short form: Conventional Commits, lowercase description, present tense.

## Reviewer shortcuts

When correcting a PR, link directly to a section here rather than re-explaining the rule. Example:

> Please use `[stock]`/`[plugin]`/`[local]`/`[custom]` markers (see [STYLE_GUIDE.md § Table type markers](STYLE_GUIDE.md#table-type-markers)).

---

*Last verified against the repo structure on **2026-05-30**.*
