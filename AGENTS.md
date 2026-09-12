# AGENTS.md

Instructions for any coding agent working in this repository, in the
[agents.md](https://agents.md/) format. Runtime-neutral by design. Claude Code
reads [`CLAUDE.md`](CLAUDE.md) as well, and the two carry the same rules.
Humans should start at [`README.md`](README.md), contributors at
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## What this repository is

A curated reference for **agent workspaces**: the roles, routines, hooks,
memory, and task coordination that make working knowledge legible to an agent.
It is documentation plus sample scaffolding, not a runnable product. Nothing
here executes on its own, and no package is published from it.

## Reading order

Read in this order when you are asked to explain or extend the repo.

1. [`PATTERNS.md`](PATTERNS.md). The eighteen load-bearing decisions, each as
   problem, pattern, why it beats the obvious alternative, and what it costs.
   This is the repo's core asset. Almost every question resolves here.
2. [`META_ARCHITECTURE.md`](META_ARCHITECTURE.md). The structural map of layers,
   modules, personas, routines, hooks, MCP servers, memory and the task layer.
3. [`WORKFLOW.md`](WORKFLOW.md). How work moves through the workspace, session
   to session.
4. [`samples/`](samples/). The scaffold library to fork: roles, skills,
   subagents, scheduled tasks, hooks, and Python helpers.
5. [`learn/`](learn/README.md) and [`teardowns/`](teardowns/README.md). The
   guided track over the patterns, and published architectures read against
   them.

Feeding the repo to a model instead of browsing it? [`docs/llms.txt`](docs/llms.txt)
is the link map and `docs/llms-full.txt` inlines the core documents in one fetch.

## Hard rule: redaction

Every commit must be safe for a public audience. Before staging anything,
scrub each changed file for personal identifiers, business or customer
specifics, credentials of any kind (never, not even as placeholders), health,
financial or legal data, and absolute paths that reveal a machine layout. Use
the generic placeholders the repo already uses: `<workspace>`, `<home>`,
`<project>`, "the user".

The automated gate runs in CI, not locally. `redaction-check.yml` calls the
scanner published as
[`jimy-r/redaction-check-action`](https://github.com/jimy-r/redaction-check-action),
and that is the check branch protection requires on every pull request. No
copy of the scanner ships in this repo, so the pre-commit step is the manual
scrub above.

When in doubt, generalise. A leak survives amendment because the push already
happened.

## Checks to run before you commit

```bash
python scripts/validate_samples.py      # sample frontmatter, links, schemas
python scripts/gen_llms_full.py --check # llms-full.txt matches its sources
python scripts/check_freshness.py       # dated stamps match git history
python tools/workspace_check.py --self-test
# redaction runs in CI (redaction-check.yml); there is no local script
```

Regenerate rather than hand-edit: `python scripts/gen_llms_full.py` rewrites
`docs/llms-full.txt`, and `python scripts/check_freshness.py --fix` rewrites the
dated stamps. CI runs these same commands, so a green local run is the gate
for all of them. Redaction is the exception: it has no local script and runs
only in CI.

## Conventions

- **Always branch.** Never commit to `main`. Branch protection blocks
  force-pushes and deletions, and requires the `redaction` check on pull
  requests.
- **One focused change per pull request.**
- **[Conventional Commits](https://www.conventionalcommits.org/):** `feat:`,
  `fix:`, `docs:`, `refactor:`, `chore:`.
- **Include a `Co-Authored-By:` trailer** on agent-assisted commits.
- **Markdown is the source of truth.** The Pages site under `docs/` is a view
  over the markdown, never the other way round.
- **Prose follows [`STYLE_GUIDE.md`](STYLE_GUIDE.md).** Anything under
  `teardowns/` gets the full editing pass before commit, because those pages
  analyse someone else's published work.
- **Roles stay pure.** Method lives in a role file, entity facts live in a
  `CONTEXT.md`, and a thin binding composes them. Schema in
  [`samples/roles/_template.md`](samples/roles/_template.md).
- **Numeric claims are derived, not typed.** Pattern and role counts are gated
  in CI against `PATTERNS.md` and `samples/roles/`. Changing one means changing
  the source, not the prose.

## Scope boundaries

Some files want issue agreement before a pull request arrives. The list is in
the Scope boundaries section of [`CONTRIBUTING.md`](CONTRIBUTING.md). Everything
else is open to direct pull requests. The repo is a curated solo reference, so a
good change can still be declined for pulling the doc off its shape.

## Where to ask

Questions and comparisons go to
[Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions).
Corrections and concrete proposals go to
[Issues](https://github.com/jimy-r/agent-workspace-architecture/issues).
Suspected privacy leaks follow [`SECURITY.md`](SECURITY.md).

---

*Last verified against the repo structure on 2026-09-06.*
