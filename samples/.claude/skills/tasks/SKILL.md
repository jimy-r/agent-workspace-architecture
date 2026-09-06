---
name: tasks
description: Use when the user says "tasks", "/tasks", "show me the tasks", "what's on the list", or "what questions are open". Concise readout of active items in To Do Notes.md and open questions in To Do Questions.md; lighter than `orient`. For outstanding work itself use /board, the canonical store.
---

## Purpose

Quick status readout of the task queue. No briefing, no recommendation — just what's on the list and what's open. Use when the user wants to see the state of work, not decide what to do next.

> **The board is now the task store.** Outstanding work lives in the task board (see the `board` module). For "what's on my plate", prefer the **`board`** skill: `python scripts/board.py stats` gives lane/owner/area counts, WIP and overdue in one shot, and it is the canonical answer.
>
> This skill remains for the *legacy* surfaces below — `To Do Notes.md` is now a raw capture inbox (un-triaged notes may sit in it), and `To Do Questions.md` is still its own store. Use it to check what has NOT yet been triaged onto the board.

## Procedure

### 1. Read

- `<workspace>/board/board.md` (via `python scripts/board.py stats`) — the canonical outstanding work
- `<workspace>/tasks/To Do Notes.md` — the raw capture inbox: report anything un-triaged (not struck through, not yet a card)
- `<workspace>/tasks/To Do Questions.md`

### 2. Parse

**Iron Law: enumerate every `##` section before filtering.** The failure mode this skill exists to prevent is silently skipping a whole section. Do not shortcut by scanning for a subset of sections you remember — list them all first, then decide per-section whether to include.

From `To Do Notes.md`:
1. First, run a `Grep` for `^## ` across the file to enumerate every section header. Write down the full list.
2. For each section in that list, decide: include or skip. Only these sections are skipped:
   - `## Completed` (historical table — always skip)
   - `## Audit Recommendations` / `## Setup Review YYYY-MM-DD` — include ONLY bullets that aren't struck through; these sections often mix done + not-done.
3. Within each included section, skip any bullet wrapped in `~~strikethrough~~`.
4. Group the surviving bullets under their `##` section header in the output.

**If a section has zero surviving bullets, omit it from the output — but you must have considered it.**

From `To Do Questions.md`:
- Include only blocks where `Status:` indicates open work. Treat these as CLOSED and skip: `REMOVED`, `COMPLETED`, `RESOLVED`, `SCOPED`, `SCAFFOLDED`, `SUPERSEDED`, `CONTEXT PROVIDED — NO ACTION REQUIRED`.
- Everything else (`PLANNED`, `DEFERRED`, `PARTIALLY COMPLETED`, `AWAITING RESPONSE`, and any status you don't recognise) is open — include it.
- For each open question: section title, date posted, and one-line summary of what's being asked or awaiting.

### 2a. Self-check before writing output

Before producing the readout:
- Did you enumerate every `##` section in `To Do Notes.md`? If you listed fewer than ~8–10 sections, you probably missed some — re-grep.
- For every section you decided to skip, can you name the reason (completed / strikethrough-only / historical table)?
- Every open-question status value you saw — did you classify it as open or closed?

If any of the three answers is "not sure", re-read the file.

### 3. Output

Structure:

**Active tasks** — grouped by section header from `To Do Notes.md`. One bullet per item, terse. Preserve the user's wording.

**Open questions** — one line per unresolved question: `- <title> (posted YYYY-MM-DD) — <one-line summary>`.

**Counts** — at the end: `N active tasks across M sections; K open questions.`

## Rules

- Do not read any other files. This is a task-queue readout, not a briefing.
- Do not recommend a next action. `orient` does that.
- Do not modify either file. Read-only.
- If a section has zero active items, omit it entirely — don't list empty sections.
- Keep the whole output under 250 words. If the queue is larger, truncate sections with `...and N more` rather than dumping everything.
