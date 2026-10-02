# E1. Cache economics

- **Question:** How much of the cache-write bill goes on first writes and how much on rewrites? Did the keep-alive pings pay for themselves, and would a different cache lifetime cost less?
- **Data:** every retained session transcript, 5,307 files dated 2026-05-11 to 2026-09-27
- **Registered:** 2026-09-27, before any analysis ran
- **Protocol hash:** none. Hashing began with E2, so this protocol was dated before the data but not hashed.
- **Run:** 2026-09-27, offline, with no model calls
- **Code:** the workspace's own analysis scripts, which are private and not published.
- **Model and engine:** no model calls. The transcripts span the Claude Code engine versions that ran in the window.
- **Status:** Adopted, because the workspace removed the keep-alive pings on 2026-09-28 after they broke even.

## Why it ran

A prompt cache bills a session's repeated prefix at a small fraction of the input price, but only once the prefix has been written, and a write costs more than plain input. When a session sits idle past the cache's lifetime, the next message writes the whole prefix again. Scans of single sessions had put these idle-gap rewrites at 44% to 69% of cache writes.

From 2026-09-08 the workspace ran a keep-alive against them. The [orient skill](../samples/.claude/skills/orient/SKILL.md) armed a no-op ping every 50 minutes, so a paused session's cache was refreshed before its one-hour lifetime ran out. The keep-alive's own registered hypothesis capped ping overhead at 2% of session cost. E1 priced the whole transcript history to test that. It also checked the program's own estimate that cache writes carry about 64% of main-thread dollars, since every later experiment reports its savings in dollars as well as tokens.

## Hypotheses

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | Idle-gap rewrites fell once the keep-alive went live | at or below 20% of interactive cache-write dollars from 2026-09-08, and lower than before | PASS (15.3%, from 51.2%) |
| H2 | The pings cost less than the rewrites they avoided | ping cost below avoided cost | FAIL ($105.83 against $105.56) |
| H3 | The main thread's 1-hour cache lifetime costs less than a 5-minute one would | 1 hour cheaper on the main thread, with the subagent result reported by sign and size | PASS (16.7% cheaper) |
| H4 | Cache writes are the main thread's largest cost | at least 50% of dollars, with the program's estimate of 64% writes, 20% reads and 16% output holding within 10 points | PASS (61.9%) |

The decision rules were fixed before the analysis.

- H1 and H2 both passing would be evidence to retain the pings at their review.
- H2 failing would be evidence for the registered kill rule, which deletes the orient step. The user decides.
- A lifetime result that favours a change comes with a recommended setting.
- An H4 failure corrects the program's unit arithmetic before anything is published.

## Method

The scan covered every transcript the workspace retains, classed from its own metadata.

| Class | Transcripts with requests | Requests |
|---|---|---|
| Interactive main thread | 1,434 | 23,869 |
| Headless main thread | 501 | 1,507 |
| Subagent | 933 | 35,040 |
| Subagent launched by a workflow script | 1,426 | 22,089 |

Requests are deduplicated by message id, and each is priced at its own model's API list rates. Main-thread writes cost 2× input on the 1-hour cache, and subagent writes 1.25× on the 5-minute one.

A cache write larger than 20% of its request's context gets a cause from the classifier in [`cache_write_scan.py`](../samples/scripts/cache_write_scan.py). The workspace's copy adds one cause the sample lacks, a change in the tool list.

| Cause | Counted as |
|---|---|
| Session start | first write |
| No cause found | first write |
| Write at or below 20% of context | first write |
| Idle gap longer than the cache lifetime | rewrite |
| Model switch | rewrite |
| Compaction | rewrite |
| Change in the tool list | rewrite |
| Edit to a standing file | rewrite |

Ping cost is every request inside a ping window. A run of pings is credited with one avoided rewrite of the prefix at the next real message, priced at the 2× write rate. The credit applies only when that gap outlived the cache.

For the lifetime question, each session was repriced twice with its pings removed. Under a 5-minute lifetime, writes cost 1.25× input and any gap over 5 minutes rewrites the full prefix. Under a 1-hour lifetime, writes cost 2× and a gap over 60 minutes does the same. For subagents, spawns of one type within an hour of each other were assumed to share a cached prefix.

## Results

| Main-thread cost by component | Share of tokens | Share of dollars |
|---|---|---|
| Cache reads | about 95% | 23.6% |
| Cache writes | about 5% | 61.9% |
| Output | about 0.5% | 14.4% |
| Uncached input | under 0.1% | 0.1% |

| Interactive main thread | Before 2026-09-08 | From 2026-09-08 |
|---|---|---|
| All rewrites, share of cache-write dollars | 60.7% | 26.7% |
| Idle-gap rewrites, share of cache-write dollars | 51.2% | 15.3% |
| Sessions with cache writes | 622 | 812 |
| Of those, sessions that ran the pings | 0 | 46 |

| The pings | Value |
|---|---|
| Sessions with pings | 47 |
| Ping runs ended by a real message | 102 |
| Of those, the gap outlived the 1-hour cache | 50 |
| Of those, the user was back inside the hour anyway | 52 |
| Ping cost, every request in a ping window | $105.83 |
| Rewrites avoided, at the 2× write rate | $105.56 |
| Rewrites avoided, net of the read still paid | $103.44 |
| Ping overhead, share of those sessions' cost | 10.05% (registered ceiling 2%) |

| Cache lifetime, pings removed | 1 hour against 5 minutes |
|---|---|
| Main thread, 1,935 sessions | 16.7% cheaper |
| Headless main thread alone, 501 sessions averaging three requests | 34.0% more expensive |
| Subagents, spawns grouped by type and parent session | 12.2% more expensive |
| Subagents, spawns grouped by type across sessions (upper bound) | 11.8% more expensive |
| Workflow subagents, grouped by type and parent session | 24.2% more expensive |

Dollar figures are API list-price equivalents.

## Verdicts

- **H1: PASS.** Idle-gap rewrites were 15.3% of interactive cache-write dollars from 2026-09-08, against 51.2% before (limit 20%). By the keep-alive's own registered criterion, under 15% of a session's write tokens, 793 of 812 sessions passed, pooled at 15.9%.
- **H2: FAIL.** The pings cost $105.83 and avoided $105.56 of rewrites, a difference of $0.27. Net of the reads still paid, they avoided $103.44.
- **H3: PASS.** With pings removed, the 1-hour lifetime cost 16.7% less than a 5-minute one would have on the main thread. For subagents a 1-hour lifetime would have cost about 12% more, and 24% more for those launched by workflow scripts. The main thread and the subagents were each already on the cheaper setting, so the result recommends no change. For the short headless sessions alone, the 1-hour lifetime cost 34.0% more than 5 minutes would have, but they share the main thread's setting.
- **H4: PASS.** Main-thread dollars split 61.9% cache writes, 23.6% cache reads, 14.4% output and 0.1% uncached input. Each share lands within 10 points of the program's earlier estimate of 64%, 20% and 16%.

## Limits the record reports

H1 tests the window rather than the pings. A ping fires only after a session has sat idle for 50 minutes, so the 46 sessions that ran them are the ones most exposed to idle gaps. Their pooled idle-gap share was 22.7%, against 15.9% across all 812 sessions, and the two figures aren't like for like.

H2 turns on $0.27 and on what counts as ping cost. Of the 720 pings, 404 drew a second request after the wakeup call returned. Counting only the first request of each ping puts the cost at $68.72, which would pass H2. The protocol priced every request in the ping window, so the verdict stands. Under either count, the overhead sits above the 2% ceiling.

The protocol assumed the main thread moved to a 1-hour cache on 2026-08-29. The usage records show 99.9% of main-thread write tokens already in the 1-hour bucket before that date, so the split at 2026-08-29 marks no change in lifetime.

The lifetime repricing has its own error. Where it should match the actual cost, it missed by 4.3%, about a quarter of the main-thread gap it reports. The subagent estimate assumes that spawns of one type share a byte-identical prefix, which is why grouping them across sessions gives an upper bound.

## What changed here

On 2026-09-28, on the H2 result, the workspace deleted the keep-alive step from its orient skill. In 52 of the 102 closed ping runs the user was back inside the hour, so those pings kept alive a cache that would not have expired. Both cache lifetimes stayed as they were, since H3 recommended no change.

This repo followed in the change that published this page. [Pattern 18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) now records the pings as tried and cut, and the [orient sample](../samples/.claude/skills/orient/SKILL.md) no longer arms the pings measured here. Pattern 18 also says the discounted reread remains the largest line on the bill. Priced per request in this workspace's main thread, cache reads came second to cache writes, at 23.6% of dollars against 61.9%.

---

*[All experiments](README.md) · Previous, [E0a. The golden set's noise floor](E0a-golden-set-noise-floor.md) · Next, [E2. Tool-output reuse](E2-tool-output-reuse.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
