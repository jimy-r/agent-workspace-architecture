---
name: wrap
description: Use when closing out a completed task to integrate it into the required files. Updates the task list, review section, meta-architecture, memory, project context, and any registry/index the change belongs in. Invoke via "wrap", "/wrap", "wrap this up", or "close out".
---

## Purpose

Stop rediscovering the integration checklist every time a task finishes. `wrap` is the canonical close-out ritual: it turns "done in the code" into "done across all the places that need to know about it."

## Iron Law

**If the task added, renamed, or removed something that lives in a registry, the registry must be updated in the same turn.** A skill without an entry in the Skills table is invisible. A new MCP server missing from META_ARCHITECTURE §7 causes drift. No exceptions.

## Procedure

### 1. Summarize what was done

One or two lines. Name the files touched and the outcome. If nothing material changed, stop here and tell the user — don't fabricate a close-out.

### 2. Update the active plan — `tasks/todo.md`

- Mark plan items complete (`[ ]` → `[x]`).
- Append or fill a `## Review` section: what was built, files created/modified, any open follow-ups.
- If `todo.md` is not the active plan for this work (e.g. plan lives in `<project>/PLAN.md`), update that instead and note it in the report.

### 3. Strike through the bullet in `tasks/To Do Notes.md`

Find the matching bullet under the correct `##` section. Wrap it in `~~...~~` and append `*(Done YYYY-MM-DD — <one-line summary with key file paths>)*`.

If the task was not on the notes list, skip this step — don't invent an entry retroactively.

### 4. Resolve any linked `tasks/To Do Questions.md` items

If an open question block is about this task, set `Status: RESOLVED` (or `COMPLETED`), add `Date resolved: YYYY-MM-DD`, and one-sentence resolution.

### 5. Registry / index sweep — THE STEP PEOPLE FORGET

Go through this table. For each row, ask: *did this task add, rename, or remove something that belongs here?* If yes, update that file in this turn.

| Change type | Registry to update |
|---|---|
| New / removed verbal shortcut | **Command Shortcuts** table in `<workspace>/CLAUDE.md` |
| New / removed custom skill | **Custom workspace skills** table in `<workspace>/META_ARCHITECTURE.md` §5 |
| New / removed custom subagent | **Workspace custom subagents** table in `META_ARCHITECTURE.md` §6 |
| New / removed scheduled task | **Scheduled tasks** table in `META_ARCHITECTURE.md` §3 |
| New / removed launcher `.bat` | **Launcher scripts** table in `META_ARCHITECTURE.md` §3 |
| New / removed MCP server | **MCP servers** table in `META_ARCHITECTURE.md` §7 |
| New / removed hook | **Hooks** table in `META_ARCHITECTURE.md` §4 |
| New / removed canonical role | `<workspace>/roles/README.md` bindings quick-reference + `META_ARCHITECTURE.md` §2 roles table |
| New project role binding | Project binding table in `META_ARCHITECTURE.md` §2 + project's `CLAUDE.md` Roles section |
| New top-level project folder | **Project layout** table in `META_ARCHITECTURE.md` §11 + `<workspace>/CLAUDE.md` Project Folders table |
| New protected-file pattern | **File protection** section in `META_ARCHITECTURE.md` §10 |
| New memory file | `MEMORY.md` index at `~/.claude/projects/<workspace-id>/memory/MEMORY.md` |
| External service signup / change / cancel | `<workspace>/Reference/services-registry.md` |
| Structural path added/moved/renamed | **Where things live** table in `META_ARCHITECTURE.md` §12 |
| Stack / deployment / customer / constraint change on a project | That project's `CONTEXT.md` |
| Medical / nutrition fact changed | `<project-health>/health_profile.md` |

**If `META_ARCHITECTURE.md` was touched, always do all of the following — no exceptions:**

1. Bump the `> **Last updated:** YYYY-MM-DD — <note>` line at the top of `<workspace>/META_ARCHITECTURE.md` with a one-paragraph summary of the structural change.
2. **Mirror the change to the public redacted copy** at `<workspace>/agent-workspace-architecture/META_ARCHITECTURE.md`. Structural changes (new row in the Skills / MCP / Scheduled-tasks / Hooks tables; new memory-system element; new §-level concept) MUST be reflected in the public copy. Paraphrase and generalise — never copy verbatim. Follow the redaction checklist in `~/.claude/projects/<workspace-id>/memory/project_workspace_architecture_repo.md` (grep checklist for specific identifier strings like `<user>`, `<user>`, `<workspace>`, `<project-platform>`, `<project-domain>`, `<city>`, `<state>`, `<password-manager>`, `<creative-project>`, etc.).
3. Bump the public repo's own `> **Last updated:**` header with a generic one-line note.
4. `cd <workspace>/agent-workspace-architecture && git status` — eyeball the diff. Run the redaction grep one more time.
5. Branch + commit + push + open PR + immediate merge. The public repo's own `CLAUDE.md` requires always branching (never commit to `main` directly). The user does not want to be the merge gatekeeper — merge immediately after opening, no waiting. With no branch protection on `main` and no required checks, `--auto` is rejected by GitHub (it only works when a PR is blocked); plain merge is the pattern.
   ```
   git checkout -b docs/<slug>
   git add -A && git commit -m "docs: <summary>"
   git push -u origin HEAD
   gh pr create --title "docs: <summary>" --body "<body>"
   gh pr merge --squash --delete-branch
   ```
6. Verify the rendered diff on GitHub immediately after merge. If you see a real identifier leak on the merged commit, open a follow-up commit to remove it immediately — amending a public commit never fully erases the leak.

The mirror + push is mandatory because the public repo's whole value is *being a current redacted snapshot*. A private META_ARCHITECTURE that drifts from the public one silently degrades the repo every week.

### 5b. Post-settings-change verification (only if applicable)

**Trigger:** any edit this session to `<home>/.claude/settings.json` (or workspace `settings.local.json` / `.claude/settings.json`) touching `permissions.allow`, `permissions.deny`, or any `hooks` block.

**Why this step exists.** Adding or removing a permission/hook only takes effect when a real fire validates it. Configuration-shape assumptions ("the pattern looks right") have silently broken scheduled tasks for days at a time — same family as the 2026-04-21 lesson ("a scheduled task isn't operational until its logs exist"). Empirical artefact (log) > config inspection.

**Procedure:**

1. List the touched files explicitly in the wrap report's `Touched:` block (settings.json edits are easy to forget).
2. Identify the next scheduled fire that exercises the changed surface:
   - Permission for `Bash(python <workspace>/scripts/*)` → next daily brief / pipeline task, or fire it now via the OS scheduler's run-on-demand command (idempotent if today's artefact already exists).
   - Permission for `gh *` / `git *` / similar audit-relevant pattern → next periodic monitoring task, or invoke the audit on-demand.
   - Hook block changes → any tool call that matches the hook's matcher. Make one explicit call (e.g. trivial `Read` for PostToolUse formatter, trivial `Bash(ls)` for PreToolUse Bash hook) and confirm the hook fired (formatter output, hook log, or system notification).
3. After the verifying fire, read `<workspace>/tasks/scheduled-logs/<skill>_<latest>.log`. Confirm:
   - The expected success sentinel (`<TASK>_OK`) is present, **OR**
   - The failure mode is unrelated to the change (e.g. a downstream MCP outage, not a permission denial on the newly-allowed pattern).
4. If the fire produced a permission denial on the very pattern that was added, the pattern syntax is wrong (glob shape, path separator, argument capture). Fix and re-verify before closing the wrap. Do not declare wrap complete on a stale config-shape assumption.

If no scheduled fire will hit the changed surface within ~24h, note it in the wrap report's `Needs user confirmation:` block so the user knows verification is pending the next natural fire.

### 6. Memory sweep

- Project state changed in a way that affects future sessions? → update the relevant `project_*.md` memory file.
- New external pointer? → add a `reference_*.md` (include `learned_on` / `last_verified` / `verify_by_checking` frontmatter).
- New feedback / correction? → add a `feedback_*.md` and note it's from this task.
- One-off event with no forward operational relevance? → `episodes/YYYY-MM-DD_<slug>.md`, NOT indexed in `MEMORY.md`.

Update `MEMORY.md` only if a new file was created or an entry was renamed/moved. Keep each entry ~150 chars, one line; index stays under 200 lines.

**Then run the memory lint:**

```
python <workspace>/scripts/memory_lint.py --fix --notes
```

`--fix` bumps `last_verified` on clean. `--notes` appends any new drift to `tasks/To Do Notes.md`. Exit 2 is fine — it means drift was found and surfaced; address in a follow-up, don't block the wrap.

### 7. Lessons check

If this task surfaced a mistake pattern worth preventing in future sessions, prepend a `## YYYY-MM-DD — <short title>` block to `tasks/lessons.md`. Skip if nothing was learned — don't pad lessons.md with platitudes.

### 8. Report

End with a tight summary:

- **Touched:** file list with one-line reason each
- **Skipped:** registries/files considered and deliberately not updated, with reason
- **Needs user confirmation:** anything requiring user decision before it can be closed (e.g. credential rotation, external signup)

## Rules

- **Do not invent history.** If a step doesn't apply (no linked question, no registry match, no lesson), say so and skip it.
- **Do not touch `tasks/HEARTBEAT.md` or `health_profile.md`** — protected by the PreToolUse hook. Use the skill SKILL.md for behaviour changes (see audit notes in META_ARCHITECTURE §3).
- **Don't overwrite another agent's work.** If you see evidence of concurrent edits (unexpected diffs, new files you didn't make), stop and ask before overwriting.
- **Don't mark tasks complete that aren't verified.** `wrap` assumes the task is already done and verified. If verification hasn't happened, run `verify-completion` first.
- **Strike-through, don't delete.** Historical bullets in `To Do Notes.md` stay visible with a done date — they're the audit trail.
