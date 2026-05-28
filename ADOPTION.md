# Adopting this pattern

A 5-step walkthrough for setting up a similar **agent workspace**, instantiated in Claude Code. Each step is independent — you don't have to do all of them, and the order below is just the path of least resistance. The Claude-Code-specific file conventions (`CLAUDE.md`, `.claude/skills/`, MCP config) are the substrate; if you're on a different agent runtime, the architectural decisions still translate even though the file shapes won't.

The full architecture is described in [META_ARCHITECTURE.md](META_ARCHITECTURE.md); this file is the "where to actually start" complement.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed and authenticated
- A working directory for your workspace (e.g. `~/workspace/`)

---

## Step 1 — Write a workspace `CLAUDE.md`

`CLAUDE.md` is the always-loaded context Claude reads when a session opens in your working directory. Keep it short — every line costs tokens on every turn.

**Minimum viable:** start with [`samples/CLAUDE.md.example`](samples/CLAUDE.md.example). Trim it to the principles you actually hold, then add a "Command shortcuts" table as you notice yourself saying the same phrase twice.

**Why it matters:** this is the foundation. Every other layer below assumes `CLAUDE.md` is loaded — roles bind against what it declares, hooks rely on paths it specifies, the heartbeat agent reads its conventions.

See: [Claude Code memory docs](https://docs.claude.com/en/docs/claude-code/memory).

---

## Step 2 — Add one canonical role

Create a `roles/` directory with one role file per expert persona you'd invoke. Start with one that matches your first real project — `security-auditor` if you want security reviews, `bookkeeper` if you want transaction categorisation, `developmental-editor` if you're drafting long-form writing.

**Minimum viable:** copy [`samples/roles/_template.md`](samples/roles/_template.md). Fill in Identity, Directives, Constraints. Add a Rationalization Table after you notice the role caving to pressure ("fine, skip the test this time").

**Why it matters:** roles are the reuse unit. A `security-auditor` that lives in `roles/` can be composed with five different projects' `CONTEXT.md` files and behave consistently. Without role extraction, security review becomes five near-identical 500-line prompts that drift from each other.

See: [Claude Code subagents docs](https://docs.claude.com/en/docs/claude-code/sub-agents).

---

## Step 3 — Wire a hook

Hooks are Claude Code's automation layer — they run shell commands on tool events. Start with a `PreToolUse` hook that protects sensitive files from accidental modification.

**Minimum viable:** drop [`samples/.claude/settings.example.json`](samples/.claude/settings.example.json) into `~/.claude/settings.json` and write a one-file `protect-files.py` that exits `2` (which blocks the tool call) when a blocked path is targeted. Typical blocklist: `.env*`, `credentials*`, `secrets*`, your financial result files, any medical data.

**Why it matters:** this is the cheapest insurance in the whole system. A ten-line hook prevents an agent that's gone sideways from rewriting your `.env` or deleting financial records. It won't catch a determined misbehaviour, but it catches the overwhelming majority of accidental damage.

See: [Claude Code hooks docs](https://docs.claude.com/en/docs/claude-code/hooks).

---

## Step 4 — Register a scheduled task

Scheduled tasks run Claude on a cadence — every 2 hours, daily, weekly. The classic starter is a "heartbeat" that reads a task list and asks clarifying questions.

**Minimum viable:** use the Claude Code app's Routines UI (or the `scheduled-tasks` MCP) to register a task. Point it at a `SKILL.md` that describes what the heartbeat does: read `tasks/To Do Notes.md`, post questions to `tasks/To Do Questions.md`, action any task where the user has answered enough questions. See [samples/tasks/README.md](samples/tasks/README.md) for the coordination layer this agent reads.

**Why it matters:** it flips the workspace from "the user remembers to follow up" to "the agent drives forward progress." Drop notes in; work gets done while you're away.

---

## Step 5 — Write your first custom skill

Skills are invokable capabilities accessed via `/<name>`. Each skill is a directory under `.claude/skills/` with a `SKILL.md` that has a CSO-style description — the description tells the loader when to invoke.

**Minimum viable:** copy [`samples/.claude/skills/orient/SKILL.md`](samples/.claude/skills/orient/SKILL.md) — it briefs a new session on the workspace state in under 300 words. Adapt the file set it reads to match your own `tasks/` layout.

**Why it matters:** skills are where you codify your own recurring workflows. Once `/orient` exists, the first 5 minutes of every session gets reliable and terse instead of exploratory.

See: [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).

---

## What to layer on next

Once the five basics above work, the harder-to-adopt parts start paying off:

- **Role binding composition** — a role (`roles/security-auditor.md`) + a project's `CONTEXT.md` = a project-scoped subagent invoked via `@project-security`. See [`samples/example-project/.claude/agents/example-security.md`](samples/example-project/.claude/agents/example-security.md).
- **Question-then-action heartbeat loop** — async progress while you're off-screen. See [`samples/tasks/README.md`](samples/tasks/README.md).
- **Typed memory files** (`user` / `feedback` / `project` / `reference`) indexed by a `MEMORY.md` — persistence across sessions.
- **MCP servers** for external capabilities — browser automation, calendar, mail.
- **Container sandboxing** for agents that touch the open web (security isolation, not reproducibility).

Adopt these when you feel the friction they solve — not before. The pattern only stays useful if each piece earns its keep.

---

*Last verified against the repo structure on **2026-04-19**. Flag drift via an Issue or correct in a PR.*
