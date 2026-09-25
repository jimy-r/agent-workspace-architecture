---
name: consolidate-memory
description: Weekly -- deep memory hygiene pass. Runs memory_lint --fix, resolves contradictions, converts relative dates, merges duplicates, archives decayed memories to memory/archive/, keeps MEMORY.md under the 25 KB ceiling. Four-op discipline per fact (ADD / UPDATE / DELETE / NOOP). Iron Laws are never consolidated away.
---

# Memory consolidation

You are firing as the scheduled `consolidate-memory` task. The memory system lives at `<home>/.claude/projects/<workspace-id>/memory/`.

## Step 1 — fix-pass + review clock

Run the structural lint with auto-fix, then read the review clock:
```
python <workspace>/scripts/memory_lint.py --fix
python <workspace>/scripts/memory_lint.py --clock
```
`--fix` repairs structure only. It does NOT touch `last_verified`, because a clean broken-link scan is not a review. `--clock` lists every topic file that carries no stamp or whose stamp is older than 90 days; take that list as the read-priority order for Step 2. Note any drift either surfaces.

**At Exit, after the gate passes, stamp only the files this run actually cross-checked:** `python <workspace>/scripts/memory_lint.py --reviewed <file.md> <file.md> ...`, naming each topic file whose claims you checked against their source of truth in Step 3. That is every UPDATEd file, every MERGE survivor, and every NOOP you verified rather than skimmed. A file you only listed or skimmed keeps its old stamp, and if you cross-checked nothing, skip the command. Never run bare `--reviewed` from this lane, because it stamps every topic file. The 2026-09-20 run did that after updating 3 files, which left 37 of 40 files on one date and tied the audit's oldest-stamp rotation key (finding b4561b39). An honest per-file stamp is what keeps the staleness clock and the rotation key meaningful (finding 7f540e62).

**Exit — route out-of-scope drift (finding 247ebd36).** Anything this pass surfaces that is outside memory scope gets appended to `<workspace>/tasks/To Do Notes.md` under `## Consolidate-memory drift`, one line: date, this log's filename, the `file:line`, and what is wrong. Surfacing into this log alone is not a route — the 2026-08-30 STRATEGY.md item sat unactioned for five days that way.

## Step 2 — read every memory

List every file under the memory directory (excluding the `archive/` and `episodes/` subfolders). Read each one fully. Build a mental map of:
- topics covered
- files referenced
- frontmatter dates
- overlap between files (>60% indicates a merge candidate)

## Step 2b — structural / regression gate: snapshot the baseline

This pass mutates a standing memory store that has NO held-out correctness scorer, so it cannot reproduce SkillOpt's behavioural-safety result (arXiv:2605.23904: an ungated weak-model self-evolution loop collapsed 0.554 -> 0.026, -52.8 pts, while its gated twin held flat; single-seed, gains only where tasks recur with a checkable signal). `memory_gate.py` is therefore a STRUCTURAL / NO-REGRESSION + INJECTION guardrail, NOT a behavioural/accuracy/safety gate.

Before applying any four-op edits, capture the baseline:
```
python <workspace>/scripts/memory_gate.py snapshot
```
It records (to `<workspace>/scripts/_state/memory_gate_snapshot.json`): per-file content+sha, total broken-reference count (via `memory_lint.lint_file`), MEMORY.md line/byte count, the `Iron Law:` line count, and the set of MEMORY.md source-of-truth pointer targets. After the edits (Steps 3-5) and before Exit you will run `memory_gate.py check` to gate the batch.

## Step 3 — four-op discipline

For each memory file, decide ONE of:

- **NOOP** — content is accurate, references resolve, no overlap. Do nothing.
- **UPDATE** — content is mostly right but a fact is stale (file moved, project status changed, date is relative). Edit in place. Convert relative dates ("last week") to absolute (`2026-05-11`).
- **MERGE** — content overlaps >60% with another file. Combine into the broader/older one; delete the narrower one; update `MEMORY.md` index to point at the survivor.
- **DELETE** — content is wholly contradicted by current source-of-truth, no longer applicable, or referenced files have vanished without successor.
- **ARCHIVE (decay / forgetting)** — content is NOT contradicted but is no longer load-bearing: superseded by a source-of-truth doc, describes a completed one-off initiative, or hasn't been relevant in 6+ months (oldest `last_verified` / mtime AND no current file references it). Move the file to `archive/` under the memory directory (create it if missing) — this preserves the content while removing it from the always-loaded set — and remove its `MEMORY.md` index entry. **Never ARCHIVE an Iron Law or an active project / source-of-truth pointer.** When you cannot confidently tell whether a memory is still load-bearing, NOOP and log it as a `forgetting-candidate` for the user to decide — never archive on a guess.

For each ADD/UPDATE/DELETE/MERGE, log a line to `<workspace>/tasks/scheduled-logs/consolidate-memory_<YYYY-MM-DD>.log`:
```
ADD path/to/file.md — <one-line reason>
UPDATE path/to/file.md — <what changed and why>
DELETE path/to/file.md — <why obsolete>
MERGE survivor.md ← absorbed.md — <reason>
ARCHIVE path/to/file.md → archive/ — <why no longer load-bearing>
forgetting-candidate path/to/file.md — <why uncertain; left for user>
```

## Step 4 — MEMORY.md ceiling

After all changes, count lines and bytes in `MEMORY.md`. If over 200 lines OR 25 KB, prune the lowest-value index entries (oldest, most-niche, least-loaded by usage). Each entry is one line, ~150 chars: `- [Title](file.md) — one-line hook`. The index is NOT a memory itself; never put memory content directly in it.

## Step 5 — Iron Law preservation

Statements prefixed `Iron Law:` in any memory file are NEVER consolidated, summarised, softened, or deleted. If a merge would touch an Iron Law, preserve it verbatim in the survivor.

## Exit

First, gate the candidate state against the Step 2b baseline:
```
python <workspace>/scripts/memory_gate.py check
```
`check` REJECTS (exit non-zero) if any of: broken-reference count increased; MEMORY.md over 200 lines or 25 KB; the `Iron Law:` line count decreased; a snapshot pointer target went missing; or the injection screen flags an untrusted-content red flag in an added line. On non-zero exit do NOT commit -- revert the batch to its pre-edit state and surface the rejection report to `<workspace>/tasks/To Do Notes.md` for human review. On exit 0, proceed.

Print a summary block:
```
Consolidate-memory cycle <YYYY-MM-DD>
  ADDed: N
  UPDATEd: N
  DELETEd: N
  MERGEd: N pairs
  ARCHIVEd (decayed topic memories): N
  forgetting-candidates flagged: N
  MEMORY.md size: <lines> lines / <bytes> bytes (limit 200 / 25K)
```
Then `CONSOLIDATE_MEMORY_OK` on a final line.
