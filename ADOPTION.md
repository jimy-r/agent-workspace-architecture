# Adopting this pattern

A 5-step walkthrough for setting up a similar **agent workspace**, instantiated in Claude Code. Each step is independent: you don't have to do all of them, and the order below is just the path of least resistance. The Claude-Code-specific file conventions (`CLAUDE.md`, `.claude/skills/`, MCP config) are the substrate; if you're on a different agent runtime, the architectural decisions still translate even though the file shapes won't.

The full architecture is described in [META_ARCHITECTURE.md](META_ARCHITECTURE.md); this file is the "where to actually start" complement.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) installed and authenticated
- A working directory for your workspace (e.g. `~/workspace/`)

---

## Step 1: Write a workspace `CLAUDE.md`

`CLAUDE.md` is the always-loaded context Claude reads when a session opens in your working directory. Keep it short; every line costs tokens on every turn.

**Minimum viable:** start with [`samples/CLAUDE.md.example`](samples/CLAUDE.md.example). Trim it to the principles you actually hold, then add a "Command shortcuts" table as you notice yourself saying the same phrase twice.

**Why it matters:** this is the foundation. Every other layer below assumes `CLAUDE.md` is loaded: roles bind against what it declares, hooks rely on paths it specifies, a delegated drain reads its conventions.

See: [Claude Code memory docs](https://docs.claude.com/en/docs/claude-code/memory).

---

## Step 2: Add one canonical role

Create a `roles/` directory with one role file per expert persona you'd invoke. Start with one that matches your first real project: `security-auditor` for security reviews, `bookkeeper` for transaction categorisation, `developmental-editor` for long-form writing.

**Minimum viable:** copy [`samples/roles/_template.md`](samples/roles/_template.md). Fill in Identity, Directives, Constraints. Add a Rationalization Table after you notice the role caving to pressure ("fine, skip the test this time").

**Why it matters:** roles are the reuse unit. A `security-auditor` that lives in `roles/` can be composed with five different projects' `CONTEXT.md` files and behave consistently. Without role extraction, security review becomes five near-identical 500-line prompts that drift from each other.

See: [Claude Code subagents docs](https://docs.claude.com/en/docs/claude-code/sub-agents).

---

## Step 3: Wire a hook

Hooks are Claude Code's automation layer; they run shell commands on tool events. Start with a `PreToolUse` hook that protects sensitive files from accidental modification.

**Minimum viable:** drop [`samples/.claude/settings.example.json`](samples/.claude/settings.example.json) into `~/.claude/settings.json` and write a one-file `protect-files.py` that exits `2` (which blocks the tool call) when a blocked path is targeted. Typical blocklist: `.env*`, `credentials*`, `secrets*`, your financial result files, any medical data.

**Why it matters:** this is the cheapest insurance in the whole system. A ten-line hook prevents an agent that's gone sideways from rewriting your `.env` or deleting financial records. It won't catch a determined misbehaviour, but it catches the overwhelming majority of accidental damage.

See: [Claude Code hooks docs](https://docs.claude.com/en/docs/claude-code/hooks).

---

## Step 4: Build a task board with an explicit delegation queue

One markdown file holds every outstanding thing as a `###` card. `status` and `area` are fields rather than sections, so moving a card is a one-line edit. Give each card a literal next action and an honest owner, and the file answers "what is actually on me" in one read.

Then add delegation. A card is agent work only when you mark it, which is the whole authorization surface.

**Minimum viable:** three pieces, no code required.

1. A cards file. Copy [`samples/board/board.example.md`](samples/board/board.example.md) and keep the field format.
2. A marker. Put `delegate: queued` on a card once you have answered four questions about it in writing: what does done look like, which folders may be written, what constrains the approach, and how should the one or two foreseeable decision points be ruled.
3. A drain you run yourself. Open a session and work the queued cards. When one hits a fork you did not pre-rule, write the question into that card's `blocked:` field and move on. See [`samples/board/agent-queue.SKILL.example.md`](samples/board/agent-queue.SKILL.example.md) for the full intake and drain procedure, and [`samples/board/README.md`](samples/board/README.md) for the card schema.

**Why it matters:** it removes the guesswork about what an agent is allowed to pick up, and it puts the context in the card at the moment you have it in your head. Questions land where you already look, so nothing waits behind a channel you never open.

**The predecessor, studied not recommended.** A scheduled "heartbeat" that reads the task list every two hours and asks clarifying questions is the classic starter, and this workspace ran one for months before retiring it. It fails in two places. The agent has to infer intent from lines written for a human reader, so it asks a lot, and its questions go to a file nobody opens. And an unattended runtime dies quietly, which here meant roughly five weeks of dark runs behind an expired credential. The design is preserved in [samples/tasks/](samples/tasks/) if you want the classifier and rejection-log ideas, both of which hold up wherever the mandate is already unambiguous.

---

## Step 5: Write your first custom skill

Skills are invokable capabilities accessed via `/<name>`. Each skill is a directory under `.claude/skills/` with a `SKILL.md` that has a CSO-style description; the description tells the loader when to invoke.

**Minimum viable:** copy [`samples/.claude/skills/orient/SKILL.md`](samples/.claude/skills/orient/SKILL.md); it briefs a new session on the workspace state in under 300 words. Adapt the file set it reads to match your own `tasks/` layout.

**Why it matters:** skills are where you codify your own recurring workflows. Once `/orient` exists, the first 5 minutes of every session gets reliable and terse instead of exploratory.

See: [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).

---

## What to layer on next

Once the five basics above work, the harder-to-adopt parts start paying off:

- **Role binding composition.** A role (`roles/security-auditor.md`) plus a project's `CONTEXT.md` makes a project-scoped subagent invoked via `@project-security`. See [`samples/example-project/.claude/agents/example-security.md`](samples/example-project/.claude/agents/example-security.md).
- **A rendered board view.** A local server that re-renders the cards file on every request and writes edits straight back to it, so no browser buffer ever holds canonical state. Add it once reading the raw markdown gets tiring. See [`samples/board/README.md`](samples/board/README.md).
- **Typed memory files** (`user` / `feedback` / `project` / `reference`) indexed by a `MEMORY.md`, for persistence across sessions.
- **MCP servers** for external capabilities: browser automation, calendar, mail.
- **Container sandboxing** for agents that touch the open web (security isolation, not reproducibility).

Adopt these when you feel the friction they solve, not before. The pattern only stays useful if each piece earns its keep.

---

*Last verified against the repo structure on **2026-08-08**. Flag drift via an Issue or correct in a PR.*
