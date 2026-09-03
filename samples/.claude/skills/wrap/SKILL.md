---
name: wrap
description: Use when closing out a completed task to integrate it into the required files. Updates the task list, review section, meta-architecture, memory, project context, and any registry/index the change belongs in. The main thread writes a close-out brief and a subagent on the execution tier does the reads and edits, so wrap costs about three main-thread steps at peak context instead of twenty. Invoke via "wrap", "/wrap", "wrap this up", or "close out".
---

## Purpose

Stop rediscovering the integration checklist every time a task finishes. `wrap` is the canonical close-out ritual: it turns "done in the code" into "done across all the places that need to know about it."

## Iron Law

**If the task added, renamed, or removed something that lives in a registry, the registry must be updated in the same turn.** A skill without an entry in the Skills table is invisible. A new MCP server missing from META_ARCHITECTURE §7 causes drift. No exceptions.

## Cost shape (why wrap is split)

Wrap runs at the end of a session, the peak of the context curve, and every tool call re-sends the whole transcript. Measured on two wrapped sessions from the "wrap" message onward, the old 20-step procedure took 22% of a 43-turn session's cache reads and 9% of a 117-turn session's, all at peak context. The split keeps the two judgment moments in the main thread (compose the brief, review the result) and moves the reads and edits into a subagent that starts near 30k tokens on the execution tier. Main-thread inferences per wrap: about three.

Two consequences bind. **The main thread does not re-read what the executor edited**; that is where the saving lives. **The executor applies text, it never composes it**; every sentence that lands in a record is written in the brief with the whole session in view. Fallback: if subagent dispatch is unavailable (headless run, tool denied), run Phase B inline in the main thread and say so under Wrap cost.

## Procedure

### Phase A — main thread, ONE message

**A1. Trivial exit.** If nothing material changed, say so and stop. Don't fabricate a close-out. If verification has not happened, run your verification skill first.

**A2. Compose the close-out brief** in the message text using the template. Every edit the executor will make is written HERE, in full. Today's date comes from the session date cross-checked against the OS clock and is passed in the brief; the executor never derives a date.

```
## Close-out brief — <task label> · Today: YYYY-MM-DD
- Done: <1–3 lines: outcome>
- Files touched: <path — why>, one per line
- Plan: tasks/todo.md block "<header>" | <project>/PLAN.md
- Plan items to tick: <list | all>
- Review text: <the full ## Review paragraph, verbatim>
- To Do Notes bullet to strike: "<quote>" | none
- Questions to resolve: "<block title>" — <one-line resolution> | none
- Registry rows: <row → file → exact change> | none
  (META touched → header-bump text + the paraphrased public-mirror change)
- CHANGELOG entry: <full text incl. a `Rollback:` clause> | none
- Memory ops: <file → ADD/UPDATE/DELETE/NOOP → the exact text> | none
- Lesson: <full `## YYYY-MM-DD — <title>` block> | none
- Settings touched: yes — <files> | no
- Token-log label: "<short label>"
- Session: <this-session-id> (your own transcript's id; B8 passes it to the token log)
```

**A3. Dispatch, in the same message.** Note the context size at wrap start (status line or `/context`) for the report, then call the `Agent` tool with `subagent_type: "general-purpose"`, `model: "sonnet"` (or your execution tier), `run_in_background: false`, and this prompt:

```
You are the wrap EXECUTOR for the <workspace> workspace. Today is YYYY-MM-DD.
Read <workspace>/.claude/skills/wrap/SKILL.md, section "Phase B — executor procedure", and follow it exactly against the brief below. Apply the text in the brief; do not compose, extend, or reinterpret it. Do not run git commands other than `git status`, do not open PRs, do not ask the user anything, do not touch files the PreToolUse guard protects. Where the world differs from the brief (text moved, item already done, signs of a concurrent edit), record the discrepancy and move on.
Write your full report to <workspace>/tasks/_state/wrap_executor_report.md and RETURN ONLY the short form given under "Executor return format" (30 lines maximum).
--- BRIEF ---
<paste the brief>
--- END BRIEF ---
```

### Phase B — executor procedure (read by the subagent)

You have the brief. Work B1 to B8 in order, batching independent commands into one message. Never write text the brief did not give you, except where a step's own script produces it. `none` on a brief line means skip that step and list it under Skipped.

**B1. Plan.** In the file named under `Plan`, tick the listed items (`[ ]` → `[x]`) and append or fill the `## Review` section with `Review text` verbatim. Prepend-ordered files keep the newest block at the top; edit in place, never re-order.

**B2. Notes.** Strike the named bullet in `tasks/To Do Notes.md` as `~~...~~` with `*(Done YYYY-MM-DD — <summary>)*` appended.

**B3. Questions.** For each named block in `tasks/To Do Questions.md`: `Status: RESOLVED`, `Date resolved: YYYY-MM-DD`, the one-line resolution.

**B4. Registries.** Apply each `Registry rows` change using the lookup table below. If `META_ARCHITECTURE.md` is touched: bump its `> **Last updated:** YYYY-MM-DD — <note>` line with the brief's text; then, if a public mirror exists, READ that repo's own `CLAUDE.md` first (it carries the contributor rules), apply the paraphrased change to the public `META_ARCHITECTURE.md`, bump its header with a generic note, run the redaction check that CLAUDE.md specifies, and STOP. Report `Public mirror: edited, redaction check <clean|HITS n>, push pending`. Add the `CHANGELOG entry` at the top of the entries in `<workspace>/CHANGELOG.md` (newest first, below the file header).

**B5. Memory.** Apply each `Memory ops` line in the memory directory. A new file also gets a one-line `MEMORY.md` index pointer (about 150 chars; index stays under 200 lines). Then `python <workspace>/scripts/memory_lint.py --fix --notes`. Exit 2 means drift was surfaced, not a failure.

**B6. Lesson.** Prepend the `Lesson` block verbatim to the top of the recent-entries part of `<workspace>/tasks/lessons.md`.

**B7. Drift scan.** `python <workspace>/scripts/wrap_drift_scan.py`. Read-only, always exits 0. Copy its `## Drift noticed` block into your file report and its `Backup staleness` line into the return.

**B8. Measurement.** `python <workspace>/scripts/token_report.py task-log --label "<Token-log label>" --session <home>/.claude/projects/<workspace-id>/<Session>.jsonl` then `python <workspace>/scripts/token_report.py log --today`. The `--session` path is mandatory: the default `latest`, run from inside a subagent, logs the subagent's own transcript and misattributes the task's cost. Both commands are fail-open: report a WARN, never retry, never block.

**Registry lookup (for B4; the brief names the rows, this maps them to files):**

| Change type | Registry to update |
|---|---|
| New / removed verbal shortcut | **Command Shortcuts** table in `<workspace>/CLAUDE.md` |
| New / removed custom skill | **Custom workspace skills** table in `<workspace>/META_ARCHITECTURE.md` §5 |
| New / removed custom subagent | **Workspace custom subagents** table in `META_ARCHITECTURE.md` §6 |
| New / removed scheduled task | **Scheduled tasks** table in `META_ARCHITECTURE.md` §3 |
| New / removed launcher script | **Launcher scripts** table in `META_ARCHITECTURE.md` §3 |
| New / removed MCP server | **MCP servers** table in `META_ARCHITECTURE.md` §7 |
| New / removed hook | **Hooks** table in `META_ARCHITECTURE.md` §4 |
| New / removed canonical role | `<workspace>/roles/README.md` bindings quick-reference + `META_ARCHITECTURE.md` §2 roles table |
| New project role binding | Project binding table in `META_ARCHITECTURE.md` §2 + project's `CLAUDE.md` Roles section |
| New top-level project folder | **Project layout** table in `META_ARCHITECTURE.md` §11 + `<workspace>/CLAUDE.md` Project Folders table |
| New protected-file pattern | **File protection** section in `META_ARCHITECTURE.md` §10 |
| New memory file | `MEMORY.md` index at `<home>/.claude/projects/<workspace-id>/memory/MEMORY.md` |
| External service signup / change / cancel | `<workspace>/Reference/services-registry.md` (password-manager item NAME only, never a value) |
| Structural path added/moved/renamed | **Where things live** table in `META_ARCHITECTURE.md` §12 |
| Stack / deployment / customer / constraint change on a project | That project's `CONTEXT.md` |
| Change to a standing surface (hook, skill, rule, scheduled task, security-envelope element) | `<workspace>/CHANGELOG.md` entry carrying a one-line `Rollback:` clause, the single action that undoes it |

**Executor return format** (30 lines maximum, nothing else):

```
WRAP EXECUTOR — <label> — YYYY-MM-DD
Touched: <path — one-line reason>, one per line
Skipped: <step — reason>, one per line
Discrepancies: <what the world said vs the brief> | none
Public mirror: not touched | edited, redaction check clean, push pending | edited, redaction check HITS n
Backup staleness: <line from the drift scan>
Drift noticed: <n> items (detail in tasks/_state/wrap_executor_report.md)
Token cost: <B8 headline> · daily row <refreshed | WARN>
```

### Phase C — main thread, one or two messages

**C1. Review the return against the brief.** Every brief line accounted for under Touched or Skipped? Resolve Discrepancies yourself: small defects fixed directly with a targeted edit; structural rework re-dispatched with corrected instructions. Do not read the edited files back wholesale; spot-check with `grep` only when the return is ambiguous.

**C2. Outward and interactive steps, batched into one message where possible:**

- **Public mirror push pending** and the redaction check was clean: the git chain as ONE shell call, then verify the rendered diff on the hosting site. A real identifier leak on the merged commit gets a follow-up commit immediately; amending never erases it.
  ```
  cd <workspace>/<public-repo> && git checkout -b docs/<slug> && git add -A && git commit -m "docs: <summary>" && git push -u origin HEAD && gh pr create --title "docs: <summary>" --body "<body>" && gh pr merge --squash --delete-branch
  ```
  The public repo's own `CLAUDE.md` requires branching; never commit to `main` directly.
- **`Settings touched: yes`** → the post-settings verification below.
- **Backup staleness** beyond your threshold → whatever backup offer your workspace carries; fresh → say nothing.

**C3. Report.** End with a tight summary:

- **Touched:** file list with one-line reason each (from the return, plus anything C1/C2 changed)
- **Skipped:** registries/files considered and deliberately not updated, with reason
- **Needs user confirmation:** anything requiring a user decision (credential rotation, external signup, a pending push, a verification awaiting its next fire)
- **Token cost:** the B8 headline, or its WARN; the daily-row line
- **Wrap cost:** context at wrap start · main-thread inferences this wrap · `executor: sonnet` or `inline fallback`
- **Drift noticed:** the B7 block, surfacing-only. These belong to other tasks; the one exception is drift caused by the task just closed, which is fixed via the registry sweep.

#### Post-settings-change verification (main thread, only if applicable)

**Trigger:** any edit this session to `<home>/.claude/settings.json` (or workspace `settings.local.json` / `.claude/settings.json`) touching `permissions.allow`, `permissions.deny`, or any `hooks` block. A permission or hook only takes effect when a real fire validates it; configuration-shape assumptions have silently broken scheduled tasks for days. Empirical artefact beats config inspection.

1. List the touched settings files in the report's Touched block.
2. Identify the next fire that exercises the changed surface: a scripts grant → the next scheduled task that uses it, or fire it on demand; `gh`/`git` grants → the next audit; hook blocks → one explicit matching tool call, and confirm the hook fired.
3. After the fire, read `<workspace>/tasks/scheduled-logs/<skill>_<latest>.log` for the success sentinel, or a failure unrelated to the change.
4. A denial on the very pattern added means the pattern syntax is wrong; fix and re-verify before closing. If no fire lands within ~24h, put it under Needs user confirmation.

## 9. Pivot bookend (only on a pivot to unrelated work)

`wrap` has persisted every durable thing to disk, so the conversation is safe to drop. If the next thing is an **unrelated** task, suggest the clean-context bookend:

1. **`/clear`** — flush the conversation (CLAUDE.md, memory, MCP reload fresh; the old session stays resumable via `/resume`).
2. **`/orient`** — cold-load the fresh strategic + active-state frame.

Skip it when continuing related work. For a *long single task* that is filling context but is not done, the tool is **`/compact`** (optionally `/compact <focus>`), not `/clear`. Both are interactive commands the user runs; `wrap` only suggests them. When context is high and the work is done, no `/compact` is needed before this wrap shape (the executor runs at small context regardless): go straight to wrap, then `/clear`. Before a break that will outlast the cache TTL and the task continues afterwards, wrap if a milestone closed, then `/compact`, so the resume re-writes a small prefix.

## Rules

- **Do not invent history.** If a step doesn't apply (no linked question, no registry match, no lesson), say so and skip it. This binds the executor as hard as the main thread.
- **The executor applies, the main thread composes.** Any text the executor would have to invent belongs in the brief. If a record came out thin, the fix is a fuller brief next time, not a smarter executor.
- **The main thread does not re-read what the executor edited.** Spot-check by `grep`, never by reading the file back.
- **Do not touch hook-protected files.** Use the skill SKILL.md for behaviour changes.
- **Don't overwrite another agent's work.** Evidence of concurrent edits (unexpected diffs, files you didn't make) is a Discrepancy for the executor and a stop-and-ask for the main thread.
- **Don't mark tasks complete that aren't verified.** `wrap` assumes the task is done and verified. If not, verify first.
- **Strike-through, don't delete.** Historical bullets in `To Do Notes.md` stay visible with a done date; they are the audit trail.
- **Fallback inline.** If dispatch is unavailable, run Phase B in the main thread and say so under Wrap cost.
