# M6. Provenance & delegation — sourced claims, mandated work

> [Learn track](README.md) · dimension: **Provenance & delegation** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can sort a task into loop, surface or keep manual and name what decided it, and hand an agent a task whose finish line someone else could check.

Two questions decide whether you can trust work you didn't watch happen. For any claim: *what is this standing on, and could I tell if the answer were nothing?* For any autonomous act: *who authorised this, and would they recognise the mandate?* A workspace that can't answer the first hands you confident sentences with nothing behind them. One that can't answer the second either nags you about everything or acts on guesses.

The delegation half carries this repo's most instructive negative result: a background agent that discovered its own work from the task list was retired after its clarifying questions piled up thirteen deep in a file nobody read, while its scheduled runtime failed dark for five weeks on an expired credential. What replaced it inverts the direction of authorisation — work reaches the agent only when a human marks it delegated, capturing intent while it's still in their head.

## The patterns

- [**Pattern 16. A claim carries its provenance, or it is a guess**](../PATTERNS.md#p16) — cite `path:line` for state claims; grade source and credibility visibly; record what would falsify a durable brief. Scope: load-bearing claims only.
- [**Pattern 14. Delegation is a queue you fill, not work the agent finds**](../PATTERNS.md#p14) — a delegated card carries done-when, write boundaries, and pre-ruled forks; questions go on the card, not into a side channel.
- [**Pattern 2. Classify-then-act, not ask-then-wait**](../PATTERNS.md#p2) — where a mandate *is* unambiguous: build the has-default work speculatively, lodge for review, log every rejection.
- [**Pattern 12. Loop selection: not everything should be a loop**](../PATTERNS.md#p12) — the four-box test (recurring, mechanically verifiable, low-judgment, headless) plus an irreversibility override that caps outward acts at surface-level autonomy.

## Do this

Two passes. (1) Run the **four-box test** on three tasks you're tempted to automate; expect at least one to come out *surface* or *keep manual* — if all three score *loop*, re-check box 3 honestly. (2) Delegate one real task properly: write the card with what done looks like, where the agent may write, and how its most likely fork should be ruled.

Pass 1 should leave three written verdicts, one per task. Any verdict other than *loop* names the box that failed, or the irreversibility override where all four passed. Pass 2 should leave a card a stranger could act on. In the [sample card format](../samples/board/README.md) that means a literal `next:` action plus body lines for `done-when:`, `write-scope:` and `ruling:`.

**Done-check:** the three verdicts are written down with the failing box named, and the delegated card's done-when is checkable by someone who didn't write it.

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

[`wrap_drift_scan.py`](../samples/scripts/wrap_drift_scan.py) is the worked *surface* case (read-only close-out scan). For provenance, sample five load-bearing claims from your agent's last substantive answer: each should carry a source or an honest `[unverified]`. Count the ones that don't.

`wrap_drift_scan.py` prints a `## Drift noticed` block with four sections and always exits 0. A source it can't find is reported inside its own section, and the scan carries on. The claim sample ends in a count out of five.

End of track. Retake the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track) and diff against your M0 baseline — that diff is the track's own done-check.

## If it didn't work

- All three tasks came out *loop*. Score each from what its script does, because the pattern records three wrong "loop this" calls made from descriptions alone. Then apply the irreversibility override. Anything that sends, posts, pays or deletes stops at *surface* whatever the boxes say.
- Your second reader can't tell when the card is done. Rewrite the done-when until it names something they can open or run, such as a file on disk or a test that passes.
- The agent hit a fork you hadn't ruled and guessed. Add the ruling to the card. If you can't rule it in advance, tell the agent to write the question on the card and stop there.
- Fewer than five of the sampled claims carry a source or a tag. That count is your baseline. Ask for `path:line` on claims about files and state, then sample again.

---

*Post the diff in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
