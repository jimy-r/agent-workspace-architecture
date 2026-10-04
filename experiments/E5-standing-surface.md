# E5. Shrinking the standing surface

- **Question:** How much of the always-loaded text the workspace writes itself can move to files read on demand, with every rule keeping its operative sentence inline, and do the moved rules still fire?
- **Data:** the workspace's own always-loaded files as they stood on 2026-09-28
- **Registered:** 2026-09-28, with the protocol hashed before any component was measured
- **Protocol:** a [redacted copy](protocols/E5-protocol.md) of the registered Protocol, Hypotheses and Decision rules sections.
- **Protocol hash:** sha256 `bacaafbfbbad0aae79168d005b36531130e34fecaa973aa78cb3972296c35923`, taken over the Protocol, Hypotheses and Decision rules sections (UTF-8, LF line endings) and saved on 2026-09-28 before any component was measured. The hash is of the private original, so the redacted copy won't match it.
- **Run:** 2026-09-28 for H1, offline and read-only. H2 and H3 are registered for a later night.
- **Code:** the workspace's own analysis scripts, which are private and not published.
- **Model and engine:** no model calls for H1, whose counts are characters divided by four. H2 is registered to replay the golden set at `claude-opus-5-5`, effort `max`.
- **Status:** Not adopted yet, because the lean variant waits on its reasoning and recall tests and on a diff the user approves.

## Why it ran

Every session opens on a floor of standing text. The project and user-level instruction files load every time, along with the memory index, the rules that aren't path-scoped and one description line per skill. The measured median floor at a session's first turn is 84,600 tokens, and two kinds of subagent load the workspace's text again at every spawn.

[Pattern 9](../PATTERNS.md#p9) treats this surface as a budget. E5 asked how much of the workspace's own part could move into files the agent opens when it needs them, and whether the rules that moved would still fire.

## Hypotheses

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | A lean variant cuts the workspace-authored floor, W | a cut of 30% or more in calibrated tokens, with every keep-list phrase present | PASS (35.7%) |
| H2 | Reasoning holds on the lean surface | paired golden-set difference, lean minus current, with its mean and lower 95% bound both at or above −0.071, the detectable effect from [E0a](E0a-golden-set-noise-floor.md) | not yet run |
| H3 | Recall holds on the lean surface | the lean arm passes at least as many of 15 recall probes as the current arm | not yet run |

The decision rules were fixed before any measurement.

- An H1 failure ends this variant, and the result names the largest remaining components for a second cut. An H1 pass schedules H2 and H3.
- Adoption needs H2 and H3 to pass, then a diff the user approves.
- A moved rule whose probe fails on the lean surface goes back inline before any adoption, whatever the overall verdict. If its probe also fails on the current surface, the rule is flagged as one that doesn't fire even inline.

## Method

W is the sum of the five components in the first results table, each read from disk. Path-scoped rules count zero, since they load only when their paths are touched. MCP servers are reported apart, because their vendors write their tool text.

Counts are characters divided by four, because the tokeniser library wasn't installed. A factor of 1.33 scales them to tokens. It is calibrated against the harness's own count for the category that holds the instruction files, memory index and rules.

The lean variant moves rationale, dated amendment history and worked cases into files read on demand. It trims memory-index pointers back to their recall triggers, and it drops text that another always-loaded source already carries ([Pattern 17](../PATTERNS.md#p17)). Every rule keeps its operative sentence inline, and every Iron Law, hard gate and credential rule stays inline. Moved text lands verbatim, so the variant relocates text and deletes none.

Two checks hold it to that. Before the variant was written, every line carrying an Iron Law, a hard gate or a credential rule got a key phrase or a stated exemption, and the variant passes only if each phrase appears verbatim in the lean always-loaded text. A no-loss check then confirms that every current line lands in the lean text or in an on-demand file.

The 15 recall probes for H3 each need one moved file to answer. Before any run, each probe's pass rule was checked against the texts. It matches the current always-loaded text and the file the probe names, and it doesn't match the lean always-loaded text.

## Results

| Component | Current tokens | Lean tokens | Cut |
|---|---|---|---|
| Project instruction file | 11,356 | 7,141 | 37.1% |
| User-level instruction file | 3,592 | 3,227 | 10.2% |
| Memory index | 6,130 | 3,679 | 40.0% |
| Three rules that load every session | 7,801 | 3,468 | 55.5% |
| Descriptions of the 29 skills the model can invoke | 2,990 | 2,990 | 0% |
| W, all five | 31,869 | 20,504 | 35.7% |

The component rows are rounded, so the lean column sums to one token more than W.

| Floor | Current | Lean |
|---|---|---|
| Median floor at a session's first turn | 84,600 | 73,235 |
| W's share of that floor | 37.7% | 28.0% |

| Check on the lean variant | Result |
|---|---|
| Keep-list phrases present in the lean always-loaded text | 45 of 45 |
| Current lines found in neither the lean text nor an on-demand file | 0 of 361 |
| On-demand files holding the moved text | 11 |
| Recall probes whose pass rule behaves as designed | 15 of 15 |

| Saving at the top-tier model's API list rates | Value |
|---|---|
| Each main-thread session start | $0.23 |
| A 100-turn main-thread session | $0.51 |
| Each subagent spawn that reloads the text | $0.14 |

The two MCP servers configured for the project add 456 tokens of deferred tool names. Counting them in W changes the cut from 35.7% to 35.2%.

## Verdicts

- **H1: PASS.** W falls from 31,869 to 20,504 calibrated tokens, a cut of 35.7% (threshold 30%). All 45 keep-list phrases are present, and none of the 361 current lines was lost.
- **H2 and H3: not yet run.** Both are registered, and the lean files and the 15 probes are frozen by hash for the run.

## Limits the record reports

Another session inserted one row into the project instruction file while the measurement ran. The variant was rebased onto the live file, and a snapshot from before the insert gives a cut of 35.8%.

The registered measure is the cut in W itself. Read instead as the fall in W's share of the whole floor, from 37.7% to 28.0%, the cut is 25.7% and would miss the threshold. The record reports that ratio beside the verdict without deciding on it.

The memory index points at topic files outside the measured scope, so the facts that the lean pointers drop weren't checked against them. Three of the 15 probes test three of those facts, and the rest need checking before any adoption. The counts also rest on one calibration reading and a character estimate, although the cut is a ratio of raw counts and the factor cancels out of it.

## What changed here

Nothing yet, and no standing file has changed. The lean variant sits unapplied until H2 and H3 report and the user approves a diff. The method that keeps the two arms apart for those runs waits on the user's choice.

---

*[All experiments](README.md) · Previous, [E3. Pricing compaction](E3-compaction-pricing.md) · Next, [E6. An orient digest](E6-orient-digest.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
