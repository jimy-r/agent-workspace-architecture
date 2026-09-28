# Experiments

This workspace runs experiments on itself. Each one asks a narrow question about cost or quality, fixes how it will answer before any data is read, and reports against thresholds set in advance. E1 to E3 run offline over the workspace's own session transcripts, pricing every request from its usage record. E0a replays the [golden set](../EVALUATION.md) twice, and E5 and E6 measure the files a session loads and reads.

Every protocol, with its hypotheses and decision rules, was written before the data it tests. From E2 onward, the sha256 of those sections was saved before the first data run and checked again at the end, so a protocol can't drift toward its result. A deviation the data forces goes into the result and never back into the protocol. Each hypothesis gets one line reading PASS, FAIL or INCONCLUSIVE. A failed hypothesis is published the same way as a passed one.

Each page gives the question, the hypotheses with their thresholds, the method in brief, the headline results, the verdicts and what changed in the workspace. Dollar figures are API list-price equivalents computed from usage records, and none of them is an account's spend.

| Status | Meaning |
|---|---|
| Adopted | The workspace changed because of the result |
| Not adopted yet | A hypothesis passed, and the change waits on a later test or an approval |
| Null result | The pre-registered test failed, and nothing changed |

## Index

| Experiment | Question | Verdict | Status | Page |
|---|---|---|---|---|
| E0a. The golden set's noise floor | What is the smallest change the golden set can detect? | H1 FAIL (0.071 against a 0.05 target), H2 PASS, H3 PASS | Adopted | [E0a](E0a-golden-set-noise-floor.md) |
| E1. Cache economics | Where does the cache-write bill go, and did the keep-alive pings pay for themselves? | H1 PASS, H2 FAIL (the pings broke even), H3 PASS, H4 PASS | Adopted | [E1](E1-cache-economics.md) |
| E2. Tool-output reuse | How much of what tool results add to context is never used again? | H1 PASS (34.5%), then H1b FAIL (21.0% against 25%) once injected content was split out | Null result | [E2](E2-tool-output-reuse.md) |
| E3. Pricing compaction | Would compacting at task boundaries or at a lower threshold cut the bill? | H1 FAIL (−2.2%), H2 FAIL (best 7.1% against 10%) | Null result | [E3](E3-compaction-pricing.md) |
| E5. Shrinking the standing surface | How much always-loaded text can move to files read on demand? | H1 PASS (a 35.7% cut), H2 and H3 not yet run | Not adopted yet | [E5](E5-standing-surface.md) |
| E6. An orient digest | Can a digest of live state replace the raw reads of the session-start skill? | H1 PASS (2.6% of the raw tokens), H2 and H3 not yet run | Not adopted yet | [E6](E6-orient-digest.md) |

Numbers missing from the table belong to experiments that are registered but haven't run, or haven't been written up here yet.

## Where the results meet the patterns

Two results bear on [Pattern 18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) as published. E1 found that cache writes, at 61.9% of main-thread dollars, are the largest cost on the bill, and that the keep-alive pings the pattern recommends broke even against the rewrites they avoided. E3 found that compacting earlier cut tokens far more than dollars. Each page names the sentence it bears on.

---

*Questions and disagreements go to [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions). Corrections are appended to the page they correct, dated.*
