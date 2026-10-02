# E3. Pricing compaction

- **Question:** In the longest main-thread sessions, what would compaction have cost and saved, in API list-price dollars, had it fired at every task boundary or at a lower context threshold than the live one?
- **Data:** the 63 longest main-thread sessions whose first request fell between 2026-08-29 and 2026-09-28, and the 60 real compactions in that window
- **Registered:** 2026-09-28, with the protocol hashed before any transcript was opened
- **Protocol hash:** sha256 `f908ae4c431f34a8a7c7a910bf5dd7b6e6aa3fecc715eb7ae5598ecf29486bf4`, taken over the Protocol, Hypotheses and Decision rules sections (UTF-8, LF line endings) and saved on 2026-09-28 before any transcript was opened. The protocol text isn't published yet, so the hash can be checked only once it is.
- **Run:** 2026-09-28, offline, with no model calls
- **Code:** the workspace's own analysis scripts, which are private and not published.
- **Model and engine:** no model calls. The transcripts span the Claude Code engine versions that ran in the window.
- **Status:** Null result, because boundary compaction and every lower threshold missed their pre-registered dollar savings.

## Why it ran

Compaction replaces a long history with a summary, so every later turn rereads a shorter prefix. In this workspace it fires automatically near the harness's 500,000-token window. The idea under test was to compact earlier, at each task boundary or at a lower threshold, and pay less for the rest of the session.

Compaction has its own price. It reads the whole prefix once and writes a summary at the output rate. Then the new, shorter prefix goes into the cache at the write rate. E3 asked whether the rereads it saves outweigh that.

## Hypotheses

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | Compacting at every task boundary saves money against the session as run | median saving across sessions of 20% or more | FAIL (−2.2%) |
| H2 | Compacting at 200k, 300k or 400k tokens saves money against the live point | median saving of 10% or more at one threshold at least | FAIL (best 7.1%, at 300k) |

The decision rules were fixed before the data.

- Each hypothesis is scored four ways. The primary pricing uses the median real summary size. Two sensitivities use the 25th and 75th percentile sizes, and a third prices every compaction's prefix as a cache read, even after the cache has expired. PASS means clearing the threshold in all four and FAIL means missing it in all four. Anything between is inconclusive.
- No verdict adopts a change. A pass would have been evidence for a fidelity test of what survives a compaction, before any setting moved.
- An H2 failure is evidence to keep the live threshold at its next review. An H1 failure is evidence against boundary compaction as a cost lever at current prices.

## Method

A session entered the sample with 300 or more turns or a peak context of 300,000 tokens or more. That picked 63 of the 1,856 main-thread sessions in the window, all of them interactive. Their median peak context was 452,800 tokens and their median starting context 84,300.

The summary size comes from the real compactions. For each of the 59 with a request on both sides, the context just after the compaction less the session's starting context gives one summary size. The median is 14,282 tokens, with quartiles at 9,142 and 24,396.

The live point is 465,000 tokens, 93% of the 500,000-token window. The 32 automatic compactions from 2026-09-15 onward fired at a median of 468,600, within 1% of it.

Task boundaries came from three signals, fixed before the data.

| Boundary signal | Signals | Boundaries it marked |
|---|---|---|
| The close-out skill ran | 50 | 17 |
| A new session block opened in the task file | 47 | 42 |
| A user message arrived after more than 60 minutes idle | 130 | 111 |
| Distinct boundaries from any signal | | 162 |

Of the 162 boundaries, 146 were compacted. Thirteen were skipped because a real compaction sat beside them, and three because the context was no larger than the new prefix.

A simulated compaction reads the prefix once and emits the summary as output. It then writes the new prefix, starting context plus summary, at the cache-write rate. When more than 60 minutes have passed since the previous request, the cache has expired and the old prefix is priced at the write rate too. Every later request in the session carries the smaller context, keeps its actual output and is priced at its own model's rates.

The summarisation call of a real compaction leaves no usage record in the main transcript, so the as-run arm is charged for its real compactions by the same rule. As a check on the replay, 20 sessions whose real compactions all fired near the live point were replayed at that point. The replay came within 3.3% of their cost as run.

## Results

| Arm | Median token saving | Median dollar saving | Pooled dollar saving |
|---|---|---|---|
| Task boundaries, against the session as run | 16.1% | −2.2% | 1.9% |
| 200k threshold, against the live point | 42.1% | 5.7% | 9.2% |
| 300k threshold, against the live point | 28.1% | 7.1% | 9.8% |
| 400k threshold, against the live point | 9.1% | 0.0% | 4.3% |

| Sample totals, API list-price equivalent | As run | Task boundaries | Change |
|---|---|---|---|
| Cache reads | $765 | $595 | −$170 |
| Cache writes | $1,170 | $1,216 | +$46 |
| Output | $631 | $705 | +$74 |
| Uncached input | $1 | $1 | $0 |
| Total | $2,567 | $2,517 | −$50 |

Most of the tokens an earlier compaction removes are cache reads, the cheapest tokens on the bill, and each compaction adds output and a cache write. At task boundaries the added cost ate most of the saving.

## Verdicts

- **H1: FAIL.** Compacting at task boundaries saved a median −2.2% of each session's cost (threshold 20%), and 1.9% pooled. The three sensitivities gave medians of −1.0%, −4.4% and 0.4%.
- **H2: FAIL.** The best median saving against the live point was 7.1%, at 300k (threshold 10%). The sensitivities' best medians were 9.2%, 4.3% and 7.1%.

## Limits the record reports

The as-run arm's compaction cost is modelled, since none of the 60 real compactions matched a logged request. Every arm pays for its compactions by the same rule, so the comparison holds, but the absolute cost of a real compaction rests on the model.

One transcript turned out to be a copy of another session and was left out. With it kept, both verdicts are unchanged. This half priced cost only. What a summary keeps was left to the fidelity half, which the rules tie to a pass.

## What changed here

Nothing. The automatic compaction point is unchanged, and this result is the evidence its next review reads.

In this repo, [Pattern 18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) lists compacting on purpose as a cost lever. In this sample, earlier compaction cut tokens by up to 42.1% at the median and dollars by at most 7.1%. [E1](E1-cache-economics.md) found the same gap between token share and dollar share on the main thread as a whole.

---

*[All experiments](README.md) · Previous, [E2. Tool-output reuse](E2-tool-output-reuse.md) · Next, [E5. Shrinking the standing surface](E5-standing-surface.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
