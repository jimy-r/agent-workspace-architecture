# E6 protocol, redacted copy

These are the Protocol, Hypotheses and Decision rules sections of [E6. An orient digest](../E6-orient-digest.md), as registered on 2026-09-28 before the data they test was read.

**This copy won't match the printed hash.** The sha256 on the E6 page (`431d73ea51b9...`) was taken over these sections of the private original. Redaction changed the bytes, so hashing this file gives a different value.

Redaction made two kinds of change and nothing else. The workspace's absolute path reads `<workspace>`. The user's name reads "the user". Workspace-relative paths, such as those under `scripts/`, name private files that aren't published, and are left as written. "The Result" means the result section of the private original, which the E6 page reports.

---

## Protocol

- **Question.** Can a deterministic digest of live state replace orient's raw reads without a worse briefing?
- **Digest.** `scripts/orient_digest.py` prints seven elements of live state and nothing else.
  1. The fired section 7 triggers, the staleness flag and the open decision-flag count, from `strategy_guard.py --json`.
  2. The count lines of `board.py stats`, its WARN lines cut before their advice clause, its blocked, overdue and delegated lines, and the live queue counts. The stale-card and no-date lists are left out.
  3. The unchecked items in the newest `tasks/todo.md` session blocks.
  4. The headers of open blocks in `tasks/To Do Questions.md`.
  5. The orient step 2 CONTEXT and PLAN files whose mtime is more than 30 days old, and any that are missing.
  6. The status line, the critical counts and every scheduled lane whose state is not FRESH, from `security_digest.py --json`. Command excerpts are never printed.
  7. The newest Part 2 lesson titles in `tasks/lessons.md`.

  The three scripts run as subprocesses, read-only, and the digest writes nothing. Every list is capped at 10 entries plus a count of the rest, and every line at 160 characters, so the output is bounded by construction. An element whose source fails prints one `unavailable` line, and the digest then exits 1.
- **Coverage.** The digest reads the windows orient reads, so the two differ only in what they print. A session block counts when its `# ` heading falls within lines 1 to 120 of `tasks/todo.md` (orient's `sed -n '1,120p'`), and it counts to its end. Lesson titles are the `## ` headings in the 40 lines that start at the `# Part 2` marker (orient's awk). The freshness list is parsed from orient's step 2 at run time. A question block is open unless its first Status line starts with one of `board.py`'s `QUESTION_CLOSED_PREFIXES`, and a block with no Status line is listed as open.
- **Raw side.** Orient's step 1 and 2 reads, re-run in Git Bash on the same day as the digest, each as the skill states it.
  - `sed -n '1,60p'` of `META_ARCHITECTURE.md`.
  - `CLAUDE.md` in full (`cat`), on its own row because sessions already carry it.
  - `sed -n '1,60p'` of `Personal/STRATEGY.md`.
  - `sed -n '1,120p'` of `tasks/todo.md`.
  - The skill's lessons awk, copied verbatim and checked against the skill text at run time.
  - `python scripts/board.py stats`.
  - `tasks/To Do Notes.md`, for which the skill names no command. The scan prints the bullet lines outside `## Completed` and outside struck `## ~~` sections, less the bullets that open struck through. The exact awk goes into the Result.
  - `tasks/To Do Questions.md`, for which the skill names no command either. It is read whole (`cat`), because closed blocks are archived out of it.
  - `ls -la` of the nine step 2 files.
  - `python scripts/security_digest.py`.

  The step 3 `strategy_guard.py` report is counted on its own row too. It sits outside the H1 total, although the digest carries its flags.
- **Counting.** Both sides use one method, `count_tokens()` imported from `scripts/ghost_token_counter.py`, applied to each command's combined stdout and stderr (what the Bash tool returns). The Result names the active tokeniser, which is tiktoken cl100k_base when installed and characters divided by 4 otherwise. Characters and UTF-8 bytes are reported beside tokens. The Read tool's line-number prefix is not added, so the raw side is a lower bound on what a Read-based orient injects.
- **Pricing.** Dollars use the rates imported from `scripts/tier_metrics.py` (`FAMILY_RATES`, `CACHE_WRITE_MULTIPLIER["main"]` and `CACHE_READ_MULTIPLIER`) for the two main-thread families in use, `fable` and `opus-5.5`. Each side is priced as one cache write, the cache read on each later turn, and the total over 100 later turns. The 100-turn horizon is a pricing convention, not a measurement.
- **Later A/B, for H2 and H3.** Ten interactive sessions that open with orient alternate a digest arm and a full arm. A coin flip, recorded in `tasks/experiments/E6/` before the first session, sets the first arm. The full arm runs the orient skill as written. The digest arm runs `python <workspace>/scripts/orient_digest.py` in place of steps 1 and 2 and keeps step 3's briefing format. Each briefing's text is saved with no arm label. After the tenth session the user rates all ten in a shuffled order, without the key, from 1 (it set me up badly) to 5 (it gave me all I needed). A follow-up read is a Read, Grep or Glob call, or a Bash call whose command starts with `cat`, `head`, `tail`, `sed`, `awk`, `grep`, `rg`, `ls`, `find` or `wc`, in the first 20 assistant requests after the briefing, one request per message id. A script counts them from the transcripts, which it opens only from inside Python. Each session's context growth across orient, taken from its usage records, is reported beside the ratings as a real-token check on H1.

## Hypotheses

- **H1, size (tonight).** The digest's output is 25% or less of the tokens of orient's step 1 and 2 raw reads, with `CLAUDE.md` left out of the raw total. The ratio with `CLAUDE.md` included and the ratio with the two unstated scans counted as zero are reported beside it, and neither decides H1.
- **H2, briefing quality (later A/B).** The digest arm's mean rating is no worse than the full arm's mean less 0.5 points, over five sessions per arm.
- **H3, follow-up reads (later A/B).** The digest arm's mean follow-up reads per session are flat or falling, at no more than the full arm's mean plus one read.

**Verdict rules.** H1 is INCONCLUSIVE if any digest element prints `unavailable` in the measured run. A raw read that fails counts as zero tokens. A PASS then stands, because a smaller raw side only makes H1 harder, and a FAIL becomes INCONCLUSIVE. With five sessions per arm, H2 and H3 can detect only a gap of about one point or one read per session, and the Result says so.

## Decision rules

- If H1 fails, the A/B does not run. The digest is cut back using the per-element table and pre-registered again.
- If H1 passes, the A/B runs as registered, and the orient skill stays as it is until H2 and H3 report.
- If H1, H2 and H3 all pass, that is evidence for a diff, which the user approves, that makes the digest orient's steps 1 and 2 and keeps the full reads as a named fallback.
- If H2 fails, the full orient stays. The lowest-rated digest briefings show which element is missing, and a revised digest is a new pre-registration.
- If H3 fails while H2 passes, the follow-up reads are tabulated by file, and the most-read file becomes a candidate element under a new pre-registration.
- If H1 is INCONCLUSIVE, the measurement re-runs under this protocol once the failing element is fixed.

**Quality guard.** H2, a blind rating with a 0.5-point non-inferiority margin.

**Budget.** Tonight, no model spend beyond the build agent. The A/B uses sessions the user runs anyway, plus one script run per session.
