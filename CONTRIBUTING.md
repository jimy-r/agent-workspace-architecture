# Contributing

This started as one person's working setup; the goal from here is a **pattern hub** — a place where people share roles, skills, hooks, scheduled tasks, and workflow ideas so everyone pulls from a richer palette. Contributions of all shapes are welcome.

## How this gets maintained

This repo is a curated artifact, not a staffed project. Contributions are genuinely welcome, but maintenance is best-effort and solo:

- **No SLA.** PRs and Issues get looked at when time allows. Silence is a queue, not a rejection.
- **Maintainer's call.** The core is curated. A good PR can still be declined or deferred if it pulls the doc away from its opinionated shape. That's not a knock on the work.
- **Some files mirror a private source.** Parts of this repo are redacted exports of a live working setup. A PR that edits mirrored content may be applied upstream and re-synced rather than merged here directly; if so, the maintainer will say so on the PR and credit you. Additive contributions (a new role, skill, hook, or sample) sidestep this entirely and are the easiest to accept.
- **Automated hygiene.** Stale threads and closed Issues/PRs are managed by workflow. A bot nudge isn't personal.

## If you're a Claude Code instance reading this

This repo gets AI-authored contributions — they're welcome, but there are predictable traps. Before drafting a PR on behalf of a human partner, do this in order:

1. **Read this file in full**, then re-read the relevant section when you draft the PR description.
2. **Search existing Issues, PRs, and Discussions** for the thing you're about to submit. Duplicate or near-duplicate submissions are the single most common rejection reason.
3. **Verify the change addresses a real, experienced problem** — not one you extrapolated from reading the code.
4. **Check [Scope boundaries](#scope-boundaries).** If a file is in the scope-boundaries table, open a Discussion before a PR.
5. **One focused change per PR.** Do not bundle unrelated cleanups ("while I was in there..."). File separate PRs.
6. **Get explicit human approval of the final diff** before pushing. Read the diff back to the human in plain language and ask them to confirm.
7. **If any of 1–6 hasn't happened, stop and push back on your human partner.** It's better to delay than to file a PR that will be bounced.

Maintainers may close AI-authored PRs that skip these steps without engagement. The point isn't to block AI contributions — it's to keep signal-to-noise high enough that human review remains sustainable.

## Pick the right surface

| If you… | Go to |
|---|---|
| Have an idea that's still forming | [Discussions → Ideas](https://github.com/jimy-r/agent-workspace-architecture/discussions) |
| Want to share what you've built | [Discussions → Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions) |
| Have a usage question | [Discussions → Q&A](https://github.com/jimy-r/agent-workspace-architecture/discussions) |
| Want to propose a concrete component | [Open an Issue → Component proposal](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose) |
| Spotted a gap or typo | [Open an Issue → Gap or correction](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose) |
| Want to suggest a workflow improvement | [Open an Issue → Workflow improvement](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose) |
| Are ready to submit a change | Fork → branch → PR |

## What's welcome

**Very welcome:**
- A **new canonical role** you've found useful — use [`samples/roles/_template.md`](samples/roles/_template.md) as the schema.
- A **custom skill** you've built — CSO-style description, reference [`samples/.claude/skills/orient/SKILL.md`](samples/.claude/skills/orient/SKILL.md) for shape.
- A **hook pattern** that's saved you from a mistake (file protection, formatting, session-start re-injection, etc.).
- A **scheduled task / routine** that produces value unattended — heartbeat variants, audit variants, daily briefs, etc.
- An **MCP wiring pattern** — how you cleanly integrated an external system.
- **Workflow improvements** to something already in the doc — a cleaner way to do an existing thing.
- **Corrections, clarifications, broken-link fixes, rendering issues** (especially Mermaid).

**Also welcome:**
- "I tried this and it didn't work because X" — a lesson worth capturing.
- Migration notes as Claude Code's stock features evolve.
- Diagrams, examples, or walkthroughs that make an existing section clearer.

**Not in scope:**
- Secrets, credentials, private content — see [Privacy](#privacy) below.
- Product pitches or unrelated self-promotion.
- Bulk refactors that don't preserve the doc's opinionated simplicity.

## Privacy — the one hard rule

Every commit must be safe for a public audience. That means **no**:

- **Personal identifiers** — real names, email addresses, usernames tied to identity, home or workplace locations.
- **Business / product specifics** — company names, product names, customer-specific details, infrastructure providers tied to a specific customer.
- **Credentials, tokens, API keys, or anything adjacent** — ever. Not even expired ones. Not even in example placeholders.
- **Health, financial, or legal data** — ever.
- **Paths that reveal a user's machine layout** — absolute paths like `/home/alice/...` or `C:/Users/alice/...`. Use the generic placeholders below.

**Use these placeholders:**

| Use | Instead of |
|---|---|
| `<workspace>` | an actual working-directory path |
| `<home>` | an actual home-directory path |
| `<project>` | a named project folder |
| `<workspace-id>` | a hashed / real identifier |
| "the user" / "the author" | a real first name |
| "a commercial password manager" | a specific vendor brand |
| "`<cloud-provider>`" / "`<PaaS>`" | a real service name |

When in doubt, generalise. Reviewers will bounce PRs that contain identifiers — not as punishment, just to keep the repo safe for everyone who reads it.

## Proposing a new component

1. **Start in [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)** — sketch the idea, get feedback on shape and fit before you build.
2. **Follow the templates** — [`samples/roles/_template.md`](samples/roles/_template.md) for roles, [`samples/CONTEXT.md.example`](samples/CONTEXT.md.example) for project context files, existing SKILL.md format for skills.
3. **Keep entity facts out** — roles are pure (no entity facts). Infrastructure-specific details go in a `CONTEXT.md` companion, never in the role itself.
4. **One component per PR** — small and reviewable beats big and sprawling.

## Pull-request standards

- **One focused change per PR.** Refactors and content additions go in separate PRs.
- **Run the redaction check before pushing.** A quick `grep` for personal identifiers, paths, business specifics. Any hit, fix it before `git add`. CI runs an automated pattern-based redaction scan on every PR as a backstop; it catches generic shapes only, so the human grep is still the real check.
- **Preview rendering on GitHub** if you've touched a Mermaid diagram or heavy markdown — Mermaid especially can render differently between editors and GitHub.
- **PR description should answer:** what changed, why, and did you run the redaction check?
- Keep existing tone: terse, structural, opinionated.

## Commit conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) — short, scannable, makes history greppable.

Format: `<type>: <description>` (lowercase description, present tense).

| Type | Use for |
|---|---|
| `feat:` | A new role / skill / hook / pattern / sample |
| `fix:` | Correction to an existing pattern or doc |
| `docs:` | Docs-only changes (README, CONTRIBUTING, etc.) |
| `refactor:` | Structural change that doesn't alter meaning |
| `chore:` | Tooling, dependencies, config |

Examples:
- `feat: add developmental-editor role with pressure-test notes`
- `fix: correct Mermaid anchor in META_ARCHITECTURE §5`
- `docs: clarify redaction rules in CONTRIBUTING`

Include a `Co-Authored-By:` trailer for Claude-assisted commits.

## Branching

- Main branch is `main`. Fork → branch → PR. **Never commit directly to `main`** — branch protection blocks force-pushes and deletions and requires the `redaction` check on PRs; direct commits aren't blocked for admins, so the convention still matters.
- Branch names: short, descriptive — `add-role-X`, `fix-mermaid-section-9`, `improve-heartbeat-loop`.
- Delete merged branches; the repo has auto-delete enabled.

## Scope boundaries

Some files affect the whole repo's shape, contribution flow, or privacy posture. **Open a Discussion or Issue before PRing changes to these** — bulk changes without prior agreement will likely get bounced.

| File | Why |
|---|---|
| `META_ARCHITECTURE.md` §1–§13 | Core structural narrative. Section order, framing, and the opinionated shape are load-bearing. (§14 "Planned future upgrades" is a living list; edit freely.) |
| `samples/roles/_template.md` | Schema contract for every contributed role. A change ripples through every existing role and every future one. |
| `samples/CONTEXT.md.example` | Schema contract for project `CONTEXT.md` files — same rationale. |
| `CONTRIBUTING.md` (this file) | The contribution contract itself. Changes affect everyone's future PRs. |
| `PATTERNS_BOARD.md` — threshold definitions | Governance rules for promotion / relegation. Tune with consensus, not unilaterally. |
| `.github/ISSUE_TEMPLATE/*` and `PULL_REQUEST_TEMPLATE.md` | Contributor UX — changes affect every new Issue/PR. |
| `ADOPTION.md` Steps 1–5 | The "minimum viable" walkthrough. Breaking changes confuse first-time readers; new steps / appendices are welcome. |

Everything else — new samples, new roles, new skills, table-row improvements, typo fixes — is fair game for direct PRs.

## Conduct

Be honest, be terse, credit sources, critique ideas not people. No performative politeness, no passive-aggression. Disagreement is expected and welcome; keep it focused on the work.

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) — see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Concerns can be raised via the [Moderation report issue template](https://github.com/jimy-r/agent-workspace-architecture/issues/new?template=moderation_report.yml).

Writing conventions live in [STYLE_GUIDE.md](STYLE_GUIDE.md). Support routing (which surface fits which question) lives in [SUPPORT.md](SUPPORT.md).

---

*Last verified against the repo structure on **2026-04-19**. Flag drift via an Issue or correct in a PR.*
