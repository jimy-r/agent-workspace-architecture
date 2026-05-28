---
name: orient
description: Use at the start of a new session when the user says "orient", "/orient", or asks to get up to speed on the agent workspace. Produces a briefing of active state, in-flight work, open questions, staleness flags, and a recommended next action.
---

## Purpose

Bring Claude up to speed on the `<workspace>/` workspace quickly and deterministically at session start, without burning context on speculative exploration. Output is a concise briefing the user can redirect.

## Iron Law

**Read the fixed file set below. Do not wander.** If a file listed here doesn't exist, note it and move on — don't improvise replacements.

## Procedure

### 1. Read (in parallel)

- `<workspace>/META_ARCHITECTURE.md` — structural reference
- `<workspace>/CLAUDE.md` — workspace working context (includes Command Shortcuts table)
- `<workspace>/tasks/todo.md` — current implementation plan
- `<workspace>/tasks/lessons.md` — self-improvement rules to apply this session
- `<workspace>/tasks/To Do Notes.md` — master task list (scan active sections; skip the `## Completed` table)
- `<workspace>/tasks/To Do Questions.md` — open heartbeat questions (skip REMOVED / COMPLETED / SCOPED / SCAFFOLDED)

### 2. Freshness scan

For each project folder that has a `CONTEXT.md` or `PLAN.md`, check mtime. Flag any older than 30 days as potentially stale. Projects to check:

- `<project-platform>/CONTEXT.md`
- `<project-finance>/CONTEXT.md`
- `<project-health>/health_profile.md`
- `<project-creative>/CONTEXT.md`
- `<project-education>/CONTEXT.md`
- `<project-resale>/PLAN.md`
- `<project-shopping>/PLAN.md`
- `<project-booking>/PLAN.md`

(Use `Glob` with mtime or `Bash` `ls -la`. Do NOT read the files — just check mtime.)

### 3. Produce the briefing

Output under 300 words, structured as:

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
