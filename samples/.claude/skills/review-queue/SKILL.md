---
name: review-queue
description: Triage the heartbeat-PR-agent review queue — walk each pending / reminded entry in tasks/HEARTBEAT_REVIEWS.md, present its artifact (REVIEW.md / PR diff / draft), and action the user's per-item decision (integrate / reject / redirect / skip). Invoke when the morning brief's "Awaiting your review" section shows 3+ items or whenever you want to drain the queue ad-hoc.
---

## Purpose

Make reviewing heartbeat-built work a one-command operation. Under the heartbeat-as-PR-agent flow, speculative builds land in `tasks/HEARTBEAT_REVIEWS.md` and wait for user decision. This skill walks the queue, presents each artifact with enough context to decide, and actions the decision — integrate / reject / redirect / skip.

## Iron Laws

- **Never auto-integrate.** Every integration requires explicit user confirmation, per item.
- **Never auto-reject.** Rejections append ADR blocks to `tasks/HEARTBEAT_REJECTIONS.md` only after capturing the user's reason + lesson.
- **Never delete source files on rejection** — only the staging artifact is removed. Source remains untouched.
- **Always record the rejection reason.** The rejection log is load-bearing for classifier tuning; silent rejections undermine the whole loop.

## Procedure

### 1. Load the queue

Read `<workspace>/tasks/HEARTBEAT_REVIEWS.md`. Parse entries under `## Active reviews` matching the format:

```
- YYYY-MM-DD | <status> | <task-slug> | <staging-location> | <summary>
```

Filter to `status == pending` OR `status == reminded`. Sort: `reminded` first (most stale), then `pending`, each sub-sorted oldest-to-newest.

If the queue is empty, print `No pending reviews. Queue is empty.` and exit.

### 2. Present each entry

For each entry, in order, print a header:

```
--- Review <N> of <M>: <task-slug> (<status>, <age> days old) ---
Summary: <summary>
Staging: <staging-location>
```

Then present the artifact based on its type:

**Staging folder** (`<path>_staging/`):
- Read the `REVIEW.md` inside. Print its contents.
- If the staging contains ≤ 3 files besides `REVIEW.md`, print each (truncated if long).

**Git worktree with PR**:
- If a PR URL is recorded in the entry, run `gh pr view <url>` and print the output.
- Otherwise, run `git -C <worktree-path> log main..HEAD --oneline` + `git -C <worktree-path> diff main --stat`.

**Git worktree without PR** (branch only):
- Show the branch name + `git log main..HEAD --oneline` + `git diff main --stat`.
- Suggest: "Run `gh pr create` to open a PR for review, or integrate the branch directly."

**Draft file** (`tasks/drafts/<slug>.md`):
- Read and print the draft (truncate if > 200 lines).

### 3. Offer the decision

After presenting each artifact, print:

```
Decide:
  (i) integrate    — accept and merge into source; remove review entry; mark task complete
  (r) reject       — delete staging; append ADR block to HEARTBEAT_REJECTIONS.md
  (x) redirect     — leave a comment for heartbeat to iterate; next cycle picks it up
  (s) skip         — leave as-is for later
  (a) all-skip     — exit the review session, leave remaining queue intact
```

Wait for the user's choice. Only proceed on a clear answer.

### 4. Action the decision

**integrate:**
- **Staging folder** → read the proposed integration command from `REVIEW.md`. Confirm with user (`Run this? y/n`). Execute. Verify source files now contain the change.
- **Git worktree + PR** → `gh pr merge <url> --squash --delete-branch` (confirm first).
- **Git worktree without PR** → offer: (a) open PR then merge, (b) fast-forward merge directly (`git merge --ff-only <branch>`), (c) cherry-pick. Execute chosen path.
- **Draft** → prompt user for final destination path, `mv` the draft there, confirm.
- After successful integration:
  - Remove the entry from `HEARTBEAT_REVIEWS.md`.
  - Mark the corresponding task in `To Do Notes.md` as complete (strike through the bullet with `~~text~~` + add `*(Done YYYY-MM-DD — integrated via review)*` suffix).

**reject:**
- Ask: `Reason (one line, for the rejection log)?` — capture answer.
- Ask: `Lesson for future attempts (one line — what would be different)?` — capture answer.
- Append to `tasks/HEARTBEAT_REJECTIONS.md` under `## Rejections`:
  ```markdown
  ## YYYY-MM-DD — <task-slug>

  **Attempted:** <summary from REVIEW.md / PR title / draft title>
  **Rejected because:** <user's reason>
  **Lesson for future attempts:** <user's lesson>
  ```
- Delete staging: `rm -rf <staging-path>` / `gh pr close <url>` + `git branch -D <branch>` / `rm <draft-path>`. Confirm per item.
- Remove the entry from `HEARTBEAT_REVIEWS.md`.

**redirect:**
- Prompt: `Redirect notes (what should heartbeat try next)?` — capture answer.
- For staging folder → write notes to `<staging>/REDIRECT.md`.
- For PR → add the notes as a PR comment via `gh pr comment <url> --body "<notes>"`.
- For draft → append notes under a `## Redirect` section in the draft.
- Leave the review entry intact. Heartbeat picks up the redirect next cycle, counts toward the rejection circuit breaker only if the *redirected* attempt is later also rejected.

**skip:**
- No changes. Move to next entry.

**all-skip:**
- Exit the review session immediately. Remaining queue unchanged.

### 5. Session summary

After all entries processed (or on `all-skip`), print:

```
Review session complete.
  Integrated: <N>
  Rejected:   <M>  (ADR blocks appended to HEARTBEAT_REJECTIONS.md)
  Redirected: <K>
  Skipped:    <L>
  Remaining in queue: <remaining count>
```

## Rules

- Present artifacts in full where practical — the user should not have to open another tool to decide.
- Never batch decisions. One entry → one decision → action → next entry.
- If integration encounters a conflict (e.g. source file changed since staging was made — the `staging-stale` case), abort that integration, flip the entry's status to `staging-stale`, print the conflict, offer to (a) re-raise for heartbeat to re-build, (b) force-integrate anyway, (c) skip.
- For rejections on items without a captured rejection reason (e.g. user just says "reject" without elaborating), ask again — do not write an empty reason into the rejection log. If the user explicitly says "no reason, just reject", record `Rejected because: (no reason given at review time)` and ask for the lesson anyway — the lesson is what future agents actually use.
- Never edit or delete existing blocks in `HEARTBEAT_REJECTIONS.md` — append-only log.

## When to invoke

- Morning brief's `## Awaiting your review` section shows **3+ items** → a focused drain session beats scrolling.
- A single item has been in `reminded` state (7+ days) and you want to triage it now rather than wait for the morning brief.
- End-of-day / end-of-week discipline — drain the queue so nothing drifts to the 14-day archive.
- Ad-hoc whenever you want to see what heartbeat has built.

## When NOT to invoke

- Queue is empty — the skill will exit immediately, but it's unnecessary noise.
- A single item with an obvious decision — just delete the staging / merge the PR directly; no skill needed.
- Mid-build of a new task — finish your current session first. The review queue waits.
