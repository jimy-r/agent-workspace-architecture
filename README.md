# agent-workspace-architecture

A blueprint for a personal **agent workspace** — personas, routines, hooks, skills, MCP servers, memory, and task coordination. This repo's worked example is built in [Claude Code](https://claude.com/claude-code) (so the file conventions you'll see — `CLAUDE.md`, `.claude/skills/`, MCP config — are Claude-Code-specific), but the *patterns* (roles library, memory hygiene, audit cadence, classify-then-act heartbeat, dead-man's-switch, tier classification by mechanical impact) port to any agent substrate. Cursor, Cline, Continue, Windsurf, custom Agent-SDK builds — pick your runtime; the architectural decisions translate.

> **Renamed 2026-05-28** from `claude-workspace-architecture`. The old URL 301-redirects; external links keep working. Rationale + framing in [CHANGELOG.md](CHANGELOG.md).

## Start here

Four paths, pick by time and setup:

- **5-minute skim** — this README, then [META_ARCHITECTURE.md](META_ARCHITECTURE.md) §1 *Layers at a glance* + §11 *Project layout*. Enough to decide if it's worth going deeper.
- **See how it actually runs** — [WORKFLOW.md](WORKFLOW.md) describes one person's day-to-day use: session discipline, entry-point choices, how tasks flow from thought to done.
- **Build your own** — walk [ADOPTION.md](ADOPTION.md) (5 steps, minimum-viable at each). Fork [`samples/`](samples/) as you go.
- **Let your agent tour it** — clone, `cd` in, launch Claude Code, then prompt:
  > *"Tour this repo. Read META_ARCHITECTURE.md, then WORKFLOW.md, then PATTERNS_BOARD.md, then scan samples/. Summarise the patterns most applicable to my workspace."*
  The repo's [`CLAUDE.md`](CLAUDE.md) auto-loads on session start, so your agent inherits the conventions before it answers.

If you know you want to contribute, jump to [CONTRIBUTING.md](CONTRIBUTING.md).

## Three ways in

Following the [Diátaxis](https://diataxis.fr/) framing, the repo's docs split across four quadrants:

- **[ADOPTION.md](ADOPTION.md)** — *tutorial*. A 5-step walkthrough for setting up a similar workspace, minimum-viable at each step. Start here if you want to build.
- **[samples/](samples/)** — *how-to*. Schematic scaffold files (CLAUDE.md and CONTEXT.md templates, a canonical role, a project binding, a custom skill, a hook config, a task list) you fork and adapt task-by-task.
- **[META_ARCHITECTURE.md](META_ARCHITECTURE.md)** — *reference*. The full structural map (~400 lines, with Mermaid diagrams). Read when you need to look up how a layer works.
- The prose throughout README + `CONTRIBUTING.md` — *explanation*. Why the shape is the way it is.

## Who this is for

Four rough tiers — all welcome:

| Tier | What they get from this |
|---|---|
| **Browsers** | A worked example of how the full Claude Code toolkit fits together end-to-end. Read `META_ARCHITECTURE.md` and move on. |
| **Adopters** | A template to build their own workspace from. Follow `ADOPTION.md`, fork `samples/`, adapt. |
| **Contributors** | A shared reference they can improve. See [CONTRIBUTING.md](CONTRIBUTING.md). |
| **Maintainers** | Someone running their own derivative as a shared hub for their team or community. Fork and re-publish. |

## What a contribution looks like

- **Roles** — fixed schema (Identity / Directives / Constraints / Method / Output / Red Flags / Rationalization Table). See [`samples/roles/_template.md`](samples/roles/_template.md) for the skeleton and [`samples/roles/security-auditor.md`](samples/roles/security-auditor.md) for a filled example. 16 more canonical roles live alongside it (accountant, researcher, tester, etc. — see [`samples/README.md`](samples/README.md)).
- **Skills** — single-file `SKILL.md` with a [CSO-style description](https://docs.claude.com/en/docs/claude-code/skills) (the trigger condition) + a procedure. See [`samples/.claude/skills/orient/SKILL.md`](samples/.claude/skills/orient/SKILL.md) and the 6 other workspace skills in the same folder.
- **Agents** — custom subagent definitions, auto-routed via CSO-style descriptions. See [`samples/.claude/agents/`](samples/.claude/agents/) for three working examples (weekly upgrade auditor, 2-hourly project-manager heartbeat, evidence-based researcher).
- **Scheduled tasks** — SKILL.md files fired by OS-level scheduler via the `run-scheduled-skill.ps1` wrapper. See [`samples/.claude/scheduled-tasks/morning-brief/SKILL.md`](samples/.claude/scheduled-tasks/morning-brief/SKILL.md) for a full daily-orchestrator pattern (email triage → receipts → bills → appointments → news → deliver).
- **Hooks** — small JSON entries wiring a shell command to a tool event. See [`samples/.claude/settings.example.json`](samples/.claude/settings.example.json).
- **Python / PowerShell helpers** — standalone utilities consumed by scheduled tasks. See [`samples/scripts/`](samples/scripts/) for ten working examples (RSS dedup, email rules engine, receipt pipeline, bill tracker, restic backup, etc.).
- **Project CONTEXT.md** — entity facts a role binding consumes. See [`samples/CONTEXT.md.example`](samples/CONTEXT.md.example).

If a pattern has worked in your own workspace, chances are it'll help someone else. Open an Issue or start a Discussion.

## What's in the doc

How a single working directory can host:

- **Roles library** — 17 canonical expert personas that compose with project-specific `CONTEXT.md` files via thin subagent bindings
- **Launcher scripts + scheduled routines** — the `.bat` layer that bootstraps sessions, plus the Claude Code app's Routines feature that is progressively replacing them
- **Hooks** — `PreToolUse` file-protection blocklist, `PostToolUse` auto-formatters, `SessionStart` context re-injection
- **Custom workspace skills** — `orient`, `wrap`, `tasks`, `verify-completion`, `systematic-debugging`, `role-pressure-test`
- **Heartbeat and audit subagents** — a 2-hourly project manager and a weekly auditor, both writing into a shared task list
- **MCP servers** — voice channel, browser automation, preview, Google Calendar + Workspace, remote chat, scheduled tasks
- **Memory system** — typed files (`user` / `feedback` / `project` / `reference`) indexed by `MEMORY.md`
- **Task coordination layer** — a question-then-action loop between the user and the heartbeat agent, backed by a small set of markdown files
- **Hardening** — a password-manager vault as the canonical credential store, `restic` backups to S3-compatible storage, and container sandboxing for external-facing agents

Tables in the doc use `[stock]` / `[plugin]` / `[local]` / `[custom]` markers so you can see what ships with Claude Code vs what someone had to write.

## Why it's shared

Nothing in here is proprietary or novel — it's just one working arrangement of the pieces Claude Code already provides. Published because a few people have asked how the whole thing fits together, and a single document is easier to hand over than a verbal tour.

The hope is that it becomes a **pattern hub** — a place where people bring their own roles, skills, hooks, scheduled tasks, and workflow ideas so everyone pulls from a richer palette than any one person can assemble solo.

## Contributing

Three surfaces, pick the right one:

- **[Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)** — sketch an idea that's still forming, ask a usage question, or share what you've built in your own workspace.
- **[Issues](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose)** — propose a concrete component (role, skill, hook, routine, MCP pattern), flag a gap or typo, or suggest a workflow improvement. Templates guide the shape.
- **Pull requests** — fork, branch, PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for standards.

**One hard rule:** no personal identifiers, no credentials, no business / health / financial specifics. Every commit must be safe for a public audience. Full guidance in [CONTRIBUTING.md](CONTRIBUTING.md).

## Caveats

- This started as one person's working setup; it's evolving into a shared reference with community contributions. The original author curates the core; contributors extend the library.
- Paths in the doc are generic (`<workspace>`, `<home>`) — any concrete setup will substitute its own.
- Nothing here executes on its own; the doc describes structure, not runnable tooling.

## Reference

- [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/overview)
- Individual feature pages linked inline throughout `META_ARCHITECTURE.md`
- [SUPPORT.md](SUPPORT.md) — where to go for what (adaptation, bugs, Q&A)
- [STYLE_GUIDE.md](STYLE_GUIDE.md) — writing and formatting conventions
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — project norms, reporting path
- [SECURITY.md](SECURITY.md) — security reporting routes (privacy leaks, workflow vulns)
- [CHANGELOG.md](CHANGELOG.md) — human-written record of notable changes
- [ATTRIBUTION.md](ATTRIBUTION.md) — credit for the patterns this repo borrows from

## License

[MIT](LICENSE). Reuse freely.

---

*Last verified against the repo structure on **2026-04-21**.*
