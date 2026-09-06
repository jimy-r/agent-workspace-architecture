---
name: orient
description: Invoke via "orient", "/orient", "get me up to speed" at the start of a fresh session - briefs active state, in-flight work, open questions, staleness flags and a recommended next action. If the prior session left a checkpoint in tasks/checkpoints/, context-restore runs first.
---

## Purpose

Bring Claude up to speed on the `<workspace>/` workspace quickly and deterministically at session start, without burning context on speculative exploration. Output is a concise briefing the user can redirect.

## Iron Law

**Read the fixed file set below. Do not wander.** If a file listed here doesn't exist, note it and move on — don't improvise replacements.

## Iron Law 2 — orient pays the highest carry cost in the session `[measured]`

Every token orient puts in context at turn 1–3 is re-read for the whole session. Measured with a token-accounting script: a turn-3 parallel Read batch (104k tokens) carried **19.6M tokens** of re-reading, against 133k for a same-sized jump at turn 182 — a 147x difference from position alone. Orient is the single most expensive act in a long session.

**So: read the TAIL, not the whole file, for the big accreting documents** (the architecture reference, the implementation-plan file, the lessons file). Their recent entries carry the live state; their history does not change what you do this session. Use `sed -n` / `tail` ranges, and pull the full file only when a task actually needs it — paid for at turn 40 instead of turn 3.

**And: when orient's own reading would exceed the tail budget** (a genuinely stale workspace, several files needing full context), dispatch `Explore` and take a summary back. Subagent transcripts are separate files, so their context never enters the main thread and carries nothing.

## Procedure

### 1. Read (in parallel — TAIL-FIRST per Iron Law 2)

- `<workspace>/META_ARCHITECTURE.md` — structural reference. **Read the header block + the most recent changelog entry only** (`sed -n '1,60p'`); the file is a rolling change log and the deep history is not session state. Full read only on an architecture task.
- `<workspace>/CLAUDE.md` — workspace working context. Read in full; it is already trimmed and it is the standing directive surface.
- `<workspace>/Personal/STRATEGY.md` — active strategic plan. **Read §1–§3 + the Last-revised block** (`sed -n '1,60p'`) for the frame; go deeper only when the session is actually strategic. **Note:** the `## Source documents` header points to synthesis + research briefs — do NOT read those during orient; flag their existence instead.
- `<workspace>/tasks/todo.md` — **most recent session block only** (`sed -n '1,120p'`). It grows into the hundreds of KB and is prepend-ordered, so the top is current work; everything below is history.
- `<workspace>/tasks/lessons.md` — **Part 1 family headings, each with its rule paragraph, + the head of Part 2** (a heads-only view: the decoy catalogues stay on disk for grep instead of loading the whole file) (`awk '/^# Part 2/{p=1} !p{ if(NR<=9){print;next} if(/^## /){print; want=1; next} if(want){ if(NF){print; want=0}; next } next } p && n++<40{print}' <workspace>/tasks/lessons.md`). The range is keyed to the `# Part 2` marker, not a line count, because Part 1 grows and shrinks at every consolidation pass and a fixed `sed -n '1,140p'` once silently cut most of the family heads once Part 1 passed that length. The `NR<=500` is a ceiling so a vanished marker cannot pull the whole file. The canonical rules live in the heads; the catalogue lines are searchable on demand, and the rest of Part 2 is one `sed` away when a session needs it.
- `python <workspace>/scripts/board.py stats` — **the canonical outstanding-work readout** (lane/owner/area counts, WIP, overdue, live queue counts). This replaces a raw notes file as the task surface; use it for the "Active state" and "In-flight work" sections. **Agent queue:** stats always prints a `delegated:` line — surface the count in "Active state", and when N queued > 0 (excluding blocked-on-user), offer a drain (`agent-queue` skill) in the recommended next action. **When the line reads `delegated: 0 queued (lane idle since …)`, carry it into "Staleness flags" as a lane-idle flag, not into Active state**: a delegation lane with no input for months looks identical to a healthy empty one, and the flag is the only thing that tells them apart.
- `<workspace>/tasks/To Do Notes.md` — now a **raw capture inbox**, not a tracker: scan only for un-triaged notes (anything not struck through and not yet a board card), and flag them for triage. Skip the `## Completed` table.
- `<workspace>/tasks/To Do Questions.md` — open questions (skip REMOVED / COMPLETED / SCOPED / SCAFFOLDED)

### 2. Freshness scan

For each project folder that has a `CONTEXT.md` or `PLAN.md`, check mtime. Flag any older than 30 days as potentially stale. Projects to check:

- `<project-platform>/CONTEXT.md`
- `<project-finance>/CONTEXT.md`
- `<project-health>/health_profile.md`
- `<project-creative>/CONTEXT.md`
- `<project-education>/CONTEXT.md`
- `<project-contracting>/CONTEXT.md`
- `<project-resale>/PLAN.md`
- `<project-shopping>/PLAN.md`
- `<project-booking>/PLAN.md`

(Use `Glob` with mtime or `Bash` `ls -la`. Do NOT read the files — just check mtime.)

Then run `python <workspace>/scripts/security_digest.py` (read-only) and fold any dead-man's-switch / scheduled-task freshness alarm into the staleness flags. This is the only interactive entry point that reads that channel — an unattended lane can die silently for weeks otherwise (a 34-day outage on a daily lane is what motivated this). If it reports clean, say nothing extra.

### 3. Produce the briefing

Output under 300 words, structured as:

**Strategic frame** — one line citing the current centre of gravity from `Personal/STRATEGY.md` (e.g. "Contract income + book + GitHub triangle; the platform project paused; absence-resilience constraint"). When STRATEGY.md has a `## Source documents` section, add a one-line note that depth is available in the synthesis + research briefs (don't enumerate them — just signal their existence so the user knows they're discoverable). Run `python <workspace>/scripts/strategy_guard.py` (read-only; parses STRATEGY.md, never edits it) and fold its deterministic flags into this same line/section: any fired date-trigger, the staleness flag if set, and the count + titles of open decision flags — so strategic drift and unactioned strategy revisions surface at session start. If the guard reports clean, say nothing extra. The guard surfaces its own standing prohibitions verbatim too, but those stay behavioural (apply them like `lessons.md`); orient need not echo the full list.

**Active state** — one line on where the workspace is right now (e.g. "No blocking work in flight; roles library + backup done; evals framework is the top strategic gap").

**In-flight work** — anything with an open plan or checklist that isn't closed. Cite file paths.

**Open questions** — unresolved items in `To Do Questions.md` that need user input.

**Staleness flags** — any CONTEXT.md / PLAN.md older than 30 days.

**Lessons active this session** — one-line summary per entry in `lessons.md`.

**Recommended next action** — one task with a one-sentence tradeoff. Present as "I'd pick X because Y; alternatives are Z" — something the user can redirect, not a decided plan.

## Rules

- Do NOT read project source code or docs beyond the file set above. The user can ask for depth on a specific project after orienting.
- Do NOT fire subagents during orient — the file set is small and bounded.
- Do NOT write to any file during orient — this is read-only.
- Do NOT include the `## Completed` historical tables in what you summarize.
- If a listed file is missing, note it in the briefing as a structural flag — don't skip silently.
- End with one question offering direction: "Want depth on any of these, or start on the recommended next action?"
