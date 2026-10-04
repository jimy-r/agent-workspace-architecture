# E1 protocol, redacted copy

These are the Protocol, Hypotheses and Decision rules sections of [E1. Cache economics](../E1-cache-economics.md), as registered on 2026-09-27 before the data they test was read.

**There is no hash to check this copy against.** Hashing began with E2, so E1's protocol was dated before the data but not hashed.

Redaction made two kinds of change and nothing else. The workspace's absolute path reads `<workspace>`. The user's name reads "the user". Workspace-relative paths, such as those under `scripts/`, name private files that aren't published, and are left as written. "The Result" means the result section of the private original, which the E1 page reports.

---

## Protocol

- **Question.** How much of the workspace's cache-write spend goes on first writes and how much on re-writes? Did the orient keep-alive cut idle-gap re-writes, and would a different cache TTL cost less?
- **Data.** Every transcript under the Claude Code project folder for `<workspace>`. That covers the main files (`*.jsonl`) and the subagent files (`*/subagents/agent-*.jsonl`) from 2026-08-07 to the run date. Each file is classed from its own metadata as interactive (entrypoint `claude-desktop`), headless (any other entrypoint) or subagent. The Result reports the rule used and the count per class.
- **Pricing.** API-equivalent dollars at the rates in `scripts/tier_metrics.py` (`FAMILY_RATES`, `CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`), imported rather than retyped and applied per model family per request. Tokens are reported beside dollars, per the user's ruling of 2026-09-27.
- **Attribution.** Write causes come from the classifier in `scripts/cache_write_scan.py`, imported. A re-write is any write it attributes to `idle-gap`, `model-switch`, `compaction`, `tool-change` or `standing-edit`. Writes attributed to `session-start` or `other` count as first writes. The scanner's own per-category totals are reported unmodified beside this grouping.
- **Keep-alive.** Ticks are identified the way `scripts/context_growth.py` identifies them. Ping cost is the dollar cost of every tick turn. The cost a run of ticks avoided is one re-write of the prefix at the next genuine user message, counted only when that gap exceeded the TTL in force.
- **TTL counterfactual.** Each main-thread session is repriced under a 5-minute TTL and under a 1-hour TTL, ignoring pings. The 5-minute TTL writes at 1.25x and re-writes the full prefix after any gap over 5 minutes. The 1-hour TTL writes at 2x and re-writes after gaps over 60 minutes. For subagents, the run estimates whether a 1-hour TTL would have turned first-request prefix writes into reads for spawns of the same type within 60 minutes of each other. That estimate is best-effort, and the Result states its method and caveats.
- **Window splits.** Before and after 2026-09-08, when the keep-alive went live. Before and after 2026-08-29, when the 1-hour TTL went live for the main thread.

## Hypotheses

- **H1, keep-alive.** In interactive main-thread sessions since 2026-09-08, idle-gap re-writes are 20% or less of cache-write dollars, and lower than before 2026-09-08. The register's own criterion (under 15% of a session's cache-write tokens) is reported beside it.
- **H2, ping cost.** Summed over sessions that have ticks, the pings cost less than the re-writes they avoided.
- **H3, TTL.** For the main thread, the 1-hour TTL costs less than a 5-minute TTL would have. For subagents, the Result reports the sign and size of the 1-hour counterfactual, with no pass threshold.
- **H4, unit.** In main-thread sessions priced per model, cache writes are the largest cost component, at 50% or more of dollars. The program's 64/20/16 split stands if each of the three shares lands within 10 points.

## Decision rules

- If H1 and H2 pass, that is evidence to keep orient step 4 at the 2026-10-08 review.
- If H2 fails, that is evidence for the register's kill rule, deleting orient step 4. The user decides at the review.
- If H3 favours a change, the Result recommends a `promptCacheTtl` or `subagentPromptCacheTtl` setting for the user to apply as a user-run settings change.
- If H4 fails, the program's unit section is corrected before anything is published.

**Quality guard.** None needed. The analysis is offline and changes no behaviour.

**Budget.** No model spend beyond the build agent and one verifier.
