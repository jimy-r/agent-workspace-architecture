# agent-workspace-architecture

A worked blueprint for a personal **agent workspace**: the roles, routines, hooks, skills, memory, and task coordination that turn a coding agent into a system you can hand work to and trust to make progress while you're away.

The example runs in [Claude Code](https://claude.com/claude-code), so the file conventions you'll see (`CLAUDE.md`, `.claude/skills/`, MCP config) are Claude-Code-specific. The architecture is not. The roles library, memory hygiene, audit cadence, classify-then-act heartbeat, dead-man's switch, and tier-by-impact gating port to Cursor, Cline, Continue, Windsurf, or a custom Agent-SDK build. Pick your runtime; the decisions translate.

This is one person's actual setup, redacted and published as a reference. Not a framework, not a product. A documented working arrangement of the pieces Claude Code already gives you, with the reasoning attached.

## What's inside

- **Roles library.** 17 pure expert personas (security-auditor, researcher, accountant, developmental-editor, and more) that compose with project `CONTEXT.md` files through thin bindings.
- **Heartbeat + audit subagents.** A 2-hourly project manager that classifies and advances the task queue, and a weekly auditor that reviews configs, security, and drift.
- **Custom skills.** `orient`, `wrap`, `tasks`, `terse-mode`, `verify-completion`, `systematic-debugging`, `role-pressure-test`.
- **Scheduled routines.** A daily morning brief (calendar, weather, AI news, task state) and a memory-consolidation pass, fired by the OS scheduler.
- **Memory system.** Typed files (`user` / `feedback` / `project` / `reference`) indexed by `MEMORY.md`, pointing at sources rather than copying them.
- **Hardening.** A `PreToolUse` file-and-command guard, a password-manager credential law, encrypted `restic` backups, and container sandboxing for web-facing agents.

Tables throughout mark each component `[stock]` / `[plugin]` / `[local]` / `[custom]`, so you can see what ships with Claude Code versus what someone had to write.

## Start with the why

If you read one thing past this page, read **[PATTERNS.md](PATTERNS.md)** — the eight load-bearing architectural decisions, each as *problem → pattern → why it beats the obvious alternative → what it costs*. That's where the actual thinking lives.

The rest of the docs follow [Diátaxis](https://diataxis.fr/):

| Quadrant | Doc | Read it for |
|---|---|---|
| Explanation | [PATTERNS.md](PATTERNS.md) | why the shape is the way it is |
| Reference | [META_ARCHITECTURE.md](META_ARCHITECTURE.md) | the full structural map, with diagrams |
| Tutorial | [ADOPTION.md](ADOPTION.md) | a 5-step build, minimum-viable at each step |
| How-to | [samples/](samples/) | scaffold files to fork and adapt |

Two more views. **[WORKFLOW.md](WORKFLOW.md)** shows a day of actually using it: session discipline, phone dispatch, how a task moves thought-to-done. And you can hand the repo to your own agent:

> *"Tour this repo. Read PATTERNS.md, then META_ARCHITECTURE.md, then WORKFLOW.md, then scan samples/. Summarise the patterns most applicable to my workspace."*

The repo's [`CLAUDE.md`](CLAUDE.md) auto-loads on session start, so your agent inherits the conventions before it answers.

## Who built this

James Ross. I design agent workspaces and AI-orchestration systems, and this is the reference version of my own. If you're standing up something similar inside an organisation, or want these patterns adapted to your stack, the practice site is **[jamesross.ai](https://jamesross.ai)**.

## Using it

Fork freely ([MIT](LICENSE)); that's what it's for. Adapt the samples, lift the patterns, localise the domain-flavoured bits (the `accountant` role is Australian-CPA shaped, the morning brief fetches Brisbane weather).

This is a **curated solo reference**, maintained best-effort. If you spot a privacy leak, a broken link, or a pattern that's plainly wrong, [open an issue](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose) and I'll get to it when time allows. Substantial PRs are welcome, but a good one can still be declined if it pulls the doc off its shape: it stays one coherent worked example, not a grab-bag.

**One hard rule for anything you send:** no personal identifiers, no credentials, no business / health / financial specifics. Every commit is safe for a public audience. Full guidance in [CONTRIBUTING.md](CONTRIBUTING.md).

## Caveats

- Paths are generic (`<workspace>`, `<home>`); a real setup substitutes its own.
- Nothing here executes on its own. The repo describes structure and ships sample code; it isn't a runnable product.
- Domain-flavoured content (Australian tax terms, Brisbane weather) is a template to localise, not a default.

## Also here

[SUPPORT.md](SUPPORT.md) (where to go for what) · [STYLE_GUIDE.md](STYLE_GUIDE.md) · [SECURITY.md](SECURITY.md) (privacy-leak and workflow-vuln reporting) · [CHANGELOG.md](CHANGELOG.md) · [ATTRIBUTION.md](ATTRIBUTION.md) (patterns this borrows from) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

The repo was renamed from `claude-workspace-architecture` on 2026-05-28; the old URL 301-redirects, so external links keep working.

## License

[MIT](LICENSE). Reuse freely.

---

*Last verified against the repo structure on 2026-05-30.*
