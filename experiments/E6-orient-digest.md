# E6. An orient digest

- **Question:** Can a deterministic digest of live state replace the raw reads of orient, the session-start skill, without a worse briefing?
- **Data:** orient's step 1 and 2 reads and the digest, both run within the same two seconds on 2026-09-28
- **Registered:** 2026-09-28, with the protocol hashed before the digest script existed
- **Run:** 2026-09-28 for H1, offline. H2 and H3 wait on a ten-session blind A/B.
- **Status:** Not adopted yet, because orient keeps its full reads until the blind A/B reports.

## Why it ran

[Orient](../samples/.claude/skills/orient/SKILL.md) is the first act of most sessions, and every token it reads is carried for the rest of the session ([Pattern 18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it)). In the session that scoped this program, orient's reads grew the context by 41,617 tokens. The briefing it writes from them runs under 300 words.

A script can pick out the live state (unchecked items, open questions, alarms and counts) and print only that. E6 built one and measured it against the reads it would replace.

## Hypotheses

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | The digest is far smaller than the raw reads | 25% or less of the tokens of orient's step 1 and 2 reads, with the project instruction file left out | PASS (2.6%) |
| H2 | The briefing is no worse | the digest arm's mean blind rating, on a 1 to 5 scale, no lower than the full arm's less 0.5 | not yet run |
| H3 | Follow-up reads stay flat | the digest arm's mean follow-up reads in the first 20 requests at most one above the full arm's | not yet run |

The decision rules were fixed before the digest existed.

- An H1 failure cuts the digest back and registers it again, with no A/B.
- An H1 pass starts the A/B, and orient stays as written until it reports.
- All three passing is evidence for a diff, approved by the user, that makes the digest orient's first two steps and keeps the full reads as a named fallback.
- An H2 failure keeps the full orient, and the lowest-rated digest briefings show which element is missing.

## Method

The digest prints seven elements of live state and nothing else.

| Element | Source |
|---|---|
| Board counts, warnings and queue counts | the board's stats command |
| Unchecked items in the newest session blocks | the task file |
| Headers of open question blocks | the questions file |
| Newest lesson titles | the lessons file |
| Status line, critical counts and scheduled lanes that aren't fresh | the security digest |
| Context files older than 30 days | file timestamps |
| Fired strategy triggers and open flag counts | the strategy check |

Every list is capped at 10 entries plus a count of the rest, and every line at 160 characters, so the output is bounded by construction. The script reads the same windows orient reads and runs read-only. A source that fails prints one `unavailable` line.

The raw side is orient's step 1 and 2 reads as the skill states them, re-run the same day. Both sides are counted the same way, as characters divided by four over each command's combined output, because the tokeniser library wasn't installed. The Read tool's line-number prefixes aren't counted, so the raw side is a lower bound on what orient injects.

Dollars price each side as one cache write, then a cache read on every later turn. The 100-turn horizon in the results is a pricing convention and not a measurement.

For H2 and H3, ten interactive sessions that open with orient will alternate between the digest and the full reads, and a coin flip recorded in advance sets the first arm. Each briefing is saved without its arm label. After the tenth session the user rates all ten in shuffled order. A script counts the follow-up reads, meaning file reads, searches and shell reads, in the first 20 requests after each briefing.

## Results

| Raw read | Tokens |
|---|---|
| Scan of the raw-capture notes file | 27,422 |
| The open-questions file, whole | 6,038 |
| Head of the strategy file | 5,774 |
| Lessons headings | 5,489 |
| Newest block of the task file | 4,416 |
| Board stats | 1,458 |
| Head of the architecture reference | 1,221 |
| Security digest | 686 |
| Listing of the context files | 208 |
| Total, the raw side of H1 | 52,712 |
| Project instruction file, counted apart because sessions already carry it | 8,467 |

| Comparison | Raw tokens | Digest tokens | Ratio |
|---|---|---|---|
| Steps 1 and 2, instruction file left out (H1) | 52,712 | 1,362 | 2.6% |
| Steps 1 and 2, instruction file counted | 61,179 | 1,362 | 2.2% |
| Steps 1 and 2, notes and questions scans set to zero | 19,252 | 1,362 | 7.1% |
| Everything orient reads, strategy report included | 64,044 | 1,362 | 2.1% |

Board counts and warnings make up 42% of the digest, the task-file items 21% and the open questions 15%.

| Saving per orient, API list rates | Top-tier model | Second-tier model |
|---|---|---|
| At the cache write | $1.03 | $0.41 |
| Over 100 later turns | $2.31 | $1.44 |

## Verdicts

- **H1: PASS.** The digest is 1,362 tokens against 52,712 for the raw reads, 2.6% (limit 25%). With the instruction file counted it is 2.2%, and with the notes and questions scans set to zero it is 7.1%.
- **H2 and H3: not yet run.** Both wait on the ten-session A/B.

## Limits the record reports

The skill names no command for the notes and questions reads, so the experiment chose its own. Those two reads make up 63.5% of the raw total. With both set to zero the digest is still 7.1% of what remains, inside the limit.

Token counts are character estimates, and the raw side leaves out the Read tool's line-number prefixes, so it is a lower bound. With five sessions per arm, H2 and H3 can only detect a gap of about one rating point or one read per session, and the protocol says so in advance.

## What changed here

Nothing yet. The digest script exists and runs read-only, and orient still performs its full reads. The A/B uses sessions the user runs anyway, at the cost of one script run each.

---

*[All experiments](README.md) · Previous, [E5. Shrinking the standing surface](E5-standing-surface.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
