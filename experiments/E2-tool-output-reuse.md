# E2. Tool-output reuse

- **Question:** Which tool results are the largest entries into the main thread's context, and how much of each is used again later in its session?
- **Data:** 1,857 main-thread sessions whose first request fell between 2026-08-29 and 2026-09-28, holding 18,482 measured tool results
- **Registered:** 2026-09-28, with the protocol hashed before any data run
- **Run:** 2026-09-28, offline, with no model calls. The follow-up, E2b, ran on 2026-09-29.
- **Status:** Null result, because once E2b separated tool output from injected content, the share never referenced fell to 21.0%, under the pre-registered 25%.

## Why it ran

A tool result enters context once and is carried on every later turn of its session. If a large share of that output is never used again, a hook that trims results before they enter context could save money. Trimming can backfire, though. A trimmed result may be fetched again, and that costs another turn. So E2 measured how much of each result is referenced later and how often the same call is repeated soon after.

## Hypothesis

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | Main-thread tool-result tokens never referenced later in their session | 25% or more | PASS (34.5%) |

A second hypothesis, that a trimming hook cuts per-task cost by 10% or more with turns up no more than 5% and judged quality no worse, needs a replay with the hook on and off. It was registered for a later pass and has not run.

The decision rules were fixed before the data run.

- A pass is evidence that a trimming hook has room to save, and aims the replay at the tools and sizes holding the most unused tokens.
- A fail means the 25% premise doesn't hold. The replay's possible saving is then capped near the measured share, and the user hears so before a replay is scheduled.
- Rereads carry no verdict. A tool reread at 20% or more goes on a watch list for the replay.

## Method

The unit is one tool result in a main-thread session. Its tokens are the growth in the next request's input, meaning that request's context less the previous request's context and output. When several results share a gap, the growth is split between them by characters.

A result counts as referenced when a later assistant message or tool input in the same session contains a distinctive span of it that the context didn't already hold.

| Span | Rule |
|---|---|
| File path | 6 or more characters with a path separator between two name characters |
| Identifier | 5 or more characters with a `_`, a case hump or a digit among letters |
| Number | 4 or more digits standing alone |
| Shingle | 8 consecutive words |

Before the full run, the matcher was checked against 40 labelled results, 20 referenced and 20 not. To pass, it had to find at least 18 of the referenced and mark at most 2 of the unreferenced. It found 18 and marked 1.

A result is reread when one of the five requests after it repeats the same call (the same file, command, search or URL). Dollars are carry cost. A result's tokens are written to the cache once at the next request, then billed at the read rate on every later request until a compaction or the end of the session.

## Results

| Main thread | Value |
|---|---|
| Measured tool results | 18,482 |
| Their tokens | 23.7M |
| Their carry cost, share of those sessions' total cost | 22.9% |
| Never referenced, share of tokens | 34.5% |
| Never referenced, share of carry dollars | 31.6% |
| Reread within five requests | 1.6% of results with a comparable call |
| Tools reread at 20% or more | none |
| Subagent transcripts, outside H1 | 32.6% of 69.3M tokens never referenced |

| Tool, main thread | Tokens | Never referenced |
|---|---|---|
| Bash | 11.7M | 22.5% |
| Read | 6.1M | 29.4% |
| Grep | 1.5M | 30.8% |
| Skill | 1.2M | 100% |

| Result size, main thread | Tokens | Never referenced |
|---|---|---|
| Under 500 | 2.1M | 75.6% |
| 500 to 1,999 | 5.2M | 41.2% |
| 2,000 to 7,999 | 9.7M | 31.1% |
| 8,000 to 31,999 | 6.5M | 20.4% |
| 32,000 and over | 0.3M | 52.0% |

## Verdict

- **H1: PASS.** 34.5% of main-thread tool-result tokens were never referenced later in their session (threshold 25%), as were 31.6% of their carry dollars.

## Limits the record reports

The method charged a gap's whole input growth to the tool results in it. But 98.6% of the measured results shared their gap with harness lines (per-turn reminders, hook output, file-change notices) or with user text, so those tokens landed on results too. A skill launch shows it most clearly. The tool returns one short line and the skill body arrives in the same gap, so every launch read as a large result nobody referenced. Counted by characters instead of apportioned tokens, the share was already 24.4%, under the threshold.

The validation drew results near the end of their sessions, so its accuracy figure leans toward short sessions and late turns. And five labelling subagents, blind to the matcher, labelled most of the validation samples where the brief had assigned that job to the experiment's own agent. That agent reread the 20 unreferenced labels before the matcher ran and changed none.

## Follow-up: E2b separates tool output from injected content

E2b was registered on 2026-09-29, with its protocol hashed before the data run. It re-ran E2's corpus and matcher with one change. Each gap's input growth was split across every block in the gap by characters, and only the tool's own output counted toward a result.

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1b | Main-thread tokens of the tool's own output never referenced later in their session | 25% or more | FAIL (21.0%) |

A pass would have aimed the replay at the pools it named. A fail withdraws the 25% premise before a replay is scheduled. E2's own verdict stands either way.

| Main thread | E2's method, re-run on the same files | E2b |
|---|---|---|
| Tokens counted as tool output | 23.8M | 15.3M |
| Never referenced, share of tokens | 34.5% | 21.0% |
| Never referenced, share of carry dollars | 31.6% | 17.3% |
| Never-referenced tokens in results of 500 tokens or more | 6.6M | 2.2M |

The sessions kept growing after E2 ran, so the re-run covers slightly more results than the table above and still gives 34.5%.

| Where the measured gaps' growth went | Share of tokens |
|---|---|
| Tool output | 64.1% |
| Harness lines (reminders, hook output, file-change notices and similar) | 28.9% |
| Injected user-role text, such as skill bodies | 4.3% |
| Images and documents | 2.5% |
| Tool references that load schemas on demand (undercounted) | 0.2% |

| Result size, tool output only | Tokens | Never referenced |
|---|---|---|
| Under 500 | 1.6M | 65.3% |
| 500 to 1,999 | 3.7M | 30.9% |
| 2,000 to 7,999 | 6.0M | 13.6% |
| 8,000 to 31,999 | 3.9M | 5.1% |

- **H1b: FAIL.** 21.0% of the main thread's tool-output tokens were never referenced (threshold 25%), along with 17.3% of their carry dollars. The registered sensitivity cuts ranged from 18.2% to 21.5%.

The verdict carries one caveat. The split charges harness lines by their characters. One kind, a snapshot of the prompt, holds far more characters than its gaps grew by, so not all harness text can be model input. A bound that gives every harness line zero tokens puts the share at 27.8%, above the threshold. That bound was added after the run and carries no verdict, so H1b stands on the registered split.

Large results get used. In results of 8,000 tokens or more, 5.1% of the output went unreferenced. In results under 500 tokens, 65.3% did, and those small results hold 1.6M tokens between them. If a trimming replay runs, its target is the unreferenced output in results of 500 tokens or more. That pool is 2.2M tokens over the month, about $65 at API list prices. Bash produced 56% of it and Read 26%.

## What changed here

No hook, rule or setting changed. The experiment program withdrew the 25% premise behind a trimming replay, and if one runs, it now aims at the 2.2M-token pool.

---

*[All experiments](README.md) · Previous, [E1. Cache economics](E1-cache-economics.md) · Next, [E3. Pricing compaction](E3-compaction-pricing.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
