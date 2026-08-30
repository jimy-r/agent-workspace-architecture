# M2. Context economics — context is spend

> [Learn track](README.md) · dimension: **Memory & context economics** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

Two facts most workspaces learn late. First, everything auto-loaded into a session — instructions, memory index, skill descriptions — costs tokens on every turn of every session, and it grows a few percent a week because no single addition is large. Second, the model API is stateless: the whole transcript is re-sent on every tool call, so a token's real cost is its size times the number of steps that follow it. A large file read at turn 3 is re-paid hundreds of times; the same read at turn 180, a handful. Size is what everyone watches. Position and step-count are what multiply it.

Neither fact argues for reading less. Reading less makes the agent dumber, which is the one saving never worth making. The levers move *where* and *when* the same information is paid for.

## The patterns

- [**Pattern 9. Context is a budget, not a constant**](../PATTERNS.md#9-context-is-a-budget-not-a-constant) — meter the always-loaded surface per source with history, alarm on trend, cap unattended runs with belts sized 10–50x normal.
- [**Pattern 18. Position is price**](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) — bulk reading goes to a subagent whose transcript is separate; ranged reads beat whole-file reads; defer big reads to the step that needs them; batch independent tool calls into one step.

## Do this

Two moves, same session. (1) Measure your always-loaded surface — every file the agent reads at session start — and write the per-file token estimate down. (2) Take the largest habitual early read in your sessions and move it: to a subagent that returns a summary, to a ranged read, or later in the session.

**Done-check:** you can name your three most expensive always-loaded sources with numbers, and one habitual read has demonstrably moved (the session start no longer contains it).

## Measure it

[`ghost_token_counter.py`](../samples/scripts/ghost_token_counter.py) is the per-source baseline with history; [`token_report.py`](../samples/scripts/token_report.py) reads real spend per session. The [context carry-cost calculator](https://jamesross.ai/tools/context-cost?utm_source=github&utm_medium=repo&utm_campaign=learn-track) prices a read by position if you want the intuition before the instrument.

Next: [M3. Verification & oversight](03-verification-oversight.md).
