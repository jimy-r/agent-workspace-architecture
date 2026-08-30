# agent-workspace-architecture

[![Redaction check](https://img.shields.io/github/actions/workflow/status/jimy-r/agent-workspace-architecture/redaction-check.yml?label=redaction)](https://github.com/jimy-r/agent-workspace-architecture/actions/workflows/redaction-check.yml)
[![Link check](https://img.shields.io/github/actions/workflow/status/jimy-r/agent-workspace-architecture/link-check.yml?label=links)](https://github.com/jimy-r/agent-workspace-architecture/actions/workflows/link-check.yml)
[![Validate samples](https://img.shields.io/github/actions/workflow/status/jimy-r/agent-workspace-architecture/validate-samples.yml?label=samples)](https://github.com/jimy-r/agent-workspace-architecture/actions/workflows/validate-samples.yml)

A reference implementation of **agent-ready knowledge architecture**: the roles, routines, hooks, skills, memory, and task coordination that make a body of working knowledge legible to AI agents, and turn a coding agent into a system you can hand work to and trust to make progress while you're away.

[![The entire architecture in one diagram: interactive, remote, and scheduled entry points feed the session, which runs with rules, typed memory, and lessons loaded; a governance floor sits under every action; state persists on one side, outputs ship past a human gate on the other, and a watcher rail checks the whole system](docs/assets/workspace-map.png)](https://jimy-r.github.io/agent-workspace-architecture/workspace-map.html)

The diagram above is the whole system — click it for the [full-page map with legend](https://jimy-r.github.io/agent-workspace-architecture/workspace-map.html), a thirty-second read.

**▶ [Take the interactive tour](https://jimy-r.github.io/agent-workspace-architecture/)** — the clickable five-minute version: the layered architecture, the eighteen load-bearing patterns, and one task moving through the system end to end.

Feeding this to a model instead? [`llms.txt`](https://jimy-r.github.io/agent-workspace-architecture/llms.txt) is the link map, and [`llms-full.txt`](https://jimy-r.github.io/agent-workspace-architecture/llms-full.txt) inlines the whole reference in a single fetch.

New work ships irregularly: patterns, teardowns, tools, and the occasional essay. Follow along at [Agent Workspaces](https://jimyr.substack.com), or watch the repo.

The example runs in [Claude Code](https://claude.com/claude-code), so the file conventions you'll see (`CLAUDE.md`, `.claude/skills/`, MCP config) are Claude-Code-specific. The architecture is not. The roles library, memory hygiene, audit cadence, explicit-delegation task board, dead-man's switch, and tier-by-impact gating port to Cursor, Cline, Continue, Windsurf, or a custom Agent-SDK build. Pick your runtime; the decisions translate.

This is one person's actual setup, redacted and published as a reference. Not a framework, not a product. A documented working arrangement of the pieces Claude Code already gives you, with the reasoning attached. It is also the reference version of the agent-ready memory layer I build for organisations, running at one-person scale.

The scale is real: 17 expert roles, 18 load-bearing patterns, an explicit-delegation task board that succeeded a retired 2-hourly heartbeat, a weekly self-audit with synthetic canaries, a dead-man's switch over scheduled jobs, and typed memory that points at sources instead of copying them — all of it running in one person's daily workspace.

## What's inside

- **Roles library.** 18 pure expert personas (security-auditor, researcher, accountant, developmental-editor, and more) that compose with project `CONTEXT.md` files through thin bindings.
- **Task board + audit subagent.** One canonical markdown card store rendered to a local served view, with an explicit delegation queue. The operator marks a card queued, a short intake interview captures what done looks like and which folders may be written, and a drain skill actions the queue inside a live session. The close-out ritual logs a per-task token record, so the metrics page charts capacity from finished work rather than from a schedule. A 2-hourly classify-then-act heartbeat held this job until August 2026. It was retired, and its design stays in [`samples/tasks/`](samples/tasks/) as the studied predecessor. Alongside sits the weekly upgrade audit, whose first job is finding improvements (public-source research plus a module-by-module critique against current best practice), with configs, security, and drift checked in the same sweep.
- **Custom skills.** `orient`, `wrap`, `tasks`, `review-queue`, `audit-workthrough`, `terse-mode`, `verify-completion`, `systematic-debugging`, `goal-design`, `role-pressure-test`.
- **Scheduled routines.** A daily morning brief (calendar, weather, AI news, task state) and a memory-consolidation pass, fired by the OS scheduler.
- **Memory system.** Typed files (`user` / `feedback` / `project` / `reference`) indexed by `MEMORY.md`, pointing at sources rather than copying them.
- **Hardening.** A `PreToolUse` file-and-command guard, a password-manager credential law, encrypted `restic` backups, and container sandboxing for web-facing agents.
- **Evaluation.** A golden set of frozen cases, each one an already-burned failure turned into a regression test, replayed K times and reported as a pass-rate with variance. Deterministic checks only, never an LLM judge, so a drop in the rate is a real regression rather than judge noise. See [EVALUATION.md](EVALUATION.md).
- **Workspace check.** A single-file, read-only linter ([`tools/workspace_check.py`](tools/workspace_check.py)) that scores your own workspace against the mechanically-checkable patterns (context budget, hook shape, permission floor, credential hygiene, skill and agent frontmatter, duplicated instruction blocks) and prints one evidence line per check.
- **The ecosystem map.** A separately maintained curated index of the wider tooling space: [awesome-agent-workspaces](https://github.com/jimy-r/awesome-agent-workspaces) — memory systems, evaluation, guardrails, observability, with a stated inclusion bar and a public rejection log.
- **Token budget.** A deterministic preflight gate that skips no-op scheduled cycles, a model-tier policy for unattended work, and daily spend telemetry feeding the weekly audit.

Tables throughout mark each component `[stock]` / `[plugin]` / `[local]` / `[custom]`, so you can see what ships with Claude Code versus what someone had to write.

## Start with the why

If you read one thing past this page, read **[PATTERNS.md](PATTERNS.md)** — the eighteen load-bearing architectural decisions, each as *problem → pattern → why it beats the obvious alternative → what it costs*. That's where the actual thinking lives.

The rest of the docs follow [Diátaxis](https://diataxis.fr/):

| Quadrant | Doc | Read it for |
|---|---|---|
| Explanation | [PATTERNS.md](PATTERNS.md) | why the shape is the way it is |
| Evidence | [teardowns/](teardowns/) | published architectures read against the patterns |
| Reference | [META_ARCHITECTURE.md](META_ARCHITECTURE.md) | the full structural map, with diagrams |
| Tutorial | [ADOPTION.md](ADOPTION.md) | a 5-step build, minimum-viable at each step |
| Tutorial | [learn/](learn/) | a guided track through the patterns, by capability, with exercises |
| Explanation | [EVALUATION.md](EVALUATION.md) | how to tell whether a workspace change actually helped |
| How-to | [samples/](samples/) | scaffold files to fork and adapt |
| How-to | [tools/workspace_check.py](tools/workspace_check.py) | run a scored check of your own workspace |

Two more views. **[WORKFLOW.md](WORKFLOW.md)** shows a day of actually using it: session discipline, phone dispatch, how a task moves thought-to-done, and the open structured-vs-autonomous tension the whole design sits inside. And you can hand the repo to your own agent:

> *"Tour this repo. Read PATTERNS.md, then META_ARCHITECTURE.md, then WORKFLOW.md, then scan samples/. Summarise the patterns most applicable to my workspace."*

The repo's [`CLAUDE.md`](CLAUDE.md) auto-loads on session start, so your agent inherits the conventions before it answers.

## Who built this

James Ross. I work as an AI Knowledge Architect; the practice is **Agent-Ready Knowledge Architecture** — making an organisation's knowledge legible to AI agents. This workspace is the reference version of my own agent-ready memory layer: the source-of-truth conventions, context architecture, and memory governance the practice teaches, running daily in production. If you're standing up something similar inside an organisation, or want these patterns adapted to your stack, the practice site is **[jamesross.ai](https://jamesross.ai/?utm_source=github&utm_medium=readme&utm_campaign=flagship)**.

## Using it

Fork freely ([MIT](LICENSE)); that's what it's for. Adapt the samples, lift the patterns, localise the domain-flavoured bits (the `accountant` role is Australian-CPA shaped, the morning brief fetches Brisbane weather).

This is a **curated solo reference**, maintained best-effort. If you spot a privacy leak, a broken link, or a pattern that's plainly wrong, [open an issue](https://github.com/jimy-r/agent-workspace-architecture/issues/new/choose) and I'll get to it when time allows. Substantial PRs are welcome, but a good one can still be declined if it pulls the doc off its shape: it stays one coherent worked example, not a grab-bag.

**One hard rule for anything you send:** no personal identifiers, no credentials, no business / health / financial specifics. Every commit is safe for a public audience. Full guidance in [CONTRIBUTING.md](CONTRIBUTING.md).

## Caveats

- Paths are generic (`<workspace>`, `<home>`); a real setup substitutes its own.
- Nothing here executes on its own. The repo describes structure and ships sample code; it isn't a runnable product.
- Domain-flavoured content (Australian tax terms, Brisbane weather) is a template to localise, not a default.

## Related

[signal-sweep](https://github.com/signal-sweep/signal-sweep): the human-gated presence tooling that grew out of this workspace's thread-sweep module, generalized to config-driven form and co-maintained as a standalone project. Its worked-example config is this repo's own topic set.

[agent-workspace-starter](https://github.com/jimy-r/agent-workspace-starter): the runnable template version of this workspace. A minimal scaffold with the session discipline and two safety hooks already running, to start a new workspace from rather than read about one.

[dead-mans-switch](https://github.com/jimy-r/dead-mans-switch): a freshness checker for scheduled agent jobs. It watches for the absence of success rather than for errors, the failure mode [pattern 3](PATTERNS.md) describes.

[redaction-check-action](https://github.com/jimy-r/redaction-check-action): a reusable GitHub Action version of a redaction gate. Scans a pull request's added lines for the shapes of private content before merge.

## Also here

[SUPPORT.md](SUPPORT.md) (where to go for what) · [STYLE_GUIDE.md](STYLE_GUIDE.md) · [SECURITY.md](SECURITY.md) (privacy-leak and workflow-vuln reporting) · [CHANGELOG.md](CHANGELOG.md) · [ATTRIBUTION.md](ATTRIBUTION.md) (patterns this borrows from) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

The repo was renamed from `claude-workspace-architecture` on 2026-05-28; the old URL 301-redirects, so external links keep working.

## License

[MIT](LICENSE). Reuse freely.

---

*Last verified against the repo structure on 2026-08-27.*
