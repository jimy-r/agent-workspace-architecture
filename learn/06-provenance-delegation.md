# M6. Provenance & delegation — sourced claims, mandated work

> [Learn track](README.md) · dimension: **Provenance & delegation** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

Two questions decide whether you can trust work you didn't watch happen. For any claim: *what is this standing on, and could I tell if the answer were nothing?* For any autonomous act: *who authorised this, and would they recognise the mandate?* A workspace that can't answer the first hands you confident sentences with nothing behind them. One that can't answer the second either nags you about everything or acts on guesses.

The delegation half carries this repo's most instructive negative result: a background agent that discovered its own work from the task list was retired after its clarifying questions piled up thirteen deep in a file nobody read, while its scheduled runtime failed dark for five weeks on an expired credential. What replaced it inverts the direction of authorisation — work reaches the agent only when a human marks it delegated, capturing intent while it's still in their head.

## The patterns

- [**Pattern 16. A claim carries its provenance, or it is a guess**](../PATTERNS.md#16-a-claim-carries-its-provenance-or-it-is-a-guess) — cite `path:line` for state claims; grade source and credibility visibly; record what would falsify a durable brief. Scope: load-bearing claims only.
- [**Pattern 14. Delegation is a queue you fill, not work the agent finds**](../PATTERNS.md#14-delegation-is-a-queue-you-fill-not-work-the-agent-finds) — a delegated card carries done-when, write boundaries, and pre-ruled forks; questions go on the card, not into a side channel.
- [**Pattern 2. Classify-then-act, not ask-then-wait**](../PATTERNS.md#2-classify-then-act-not-ask-then-wait) — where a mandate *is* unambiguous: build the has-default work speculatively, lodge for review, log every rejection.
- [**Pattern 12. Loop selection: not everything should be a loop**](../PATTERNS.md#12-loop-selection-not-everything-should-be-a-loop) — the four-box test (recurring, mechanically verifiable, low-judgment, headless) plus an irreversibility override that caps outward acts at surface-level autonomy.

## Do this

Two passes. (1) Run the **four-box test** on three tasks you're tempted to automate; expect at least one to come out *surface* or *keep manual* — if all three score *loop*, re-check box 3 honestly. (2) Delegate one real task properly: write the card with what done looks like, where the agent may write, and how its most likely fork should be ruled.

**Done-check:** the three verdicts are written down with the failing box named, and the delegated card's done-when is checkable by someone who didn't write it.

## Measure it

[`wrap_drift_scan.py`](../samples/scripts/wrap_drift_scan.py) is the worked *surface* case (read-only close-out scan). For provenance, sample five load-bearing claims from your agent's last substantive answer: each should carry a source or an honest `[unverified]`. Count the ones that don't.

End of track. Retake the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track) and diff against your M0 baseline — that diff is the track's own done-check.
