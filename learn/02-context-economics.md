# M2. Context economics — context is spend

> [Learn track](README.md) · dimension: **Memory & context economics** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can put a token figure on each file your agent loads before you type, and move one costly read to a cheaper place in the session.

Two facts most workspaces learn late. First, everything auto-loaded into a session — instructions, memory index, skill descriptions — costs tokens on every turn of every session, and it grows a few percent a week because no single addition is large. Second, the model API is stateless: the whole transcript is re-sent on every tool call, so a token's real cost is its size times the number of steps that follow it. A large file read at turn 3 is re-paid hundreds of times; the same read at turn 180, a handful. Size is what everyone watches. Position and step-count are what multiply it.

Neither fact argues for reading less. Reading less makes the agent dumber, which is the one saving never worth making. The levers move *where* and *when* the same information is paid for.

## The patterns

- [**Pattern 9. Context is a budget, not a constant**](../PATTERNS.md#p9) — meter the always-loaded surface per source with history, alarm on trend, cap unattended runs with belts sized 10–50x normal.
- [**Pattern 18. Position is price**](../PATTERNS.md#p18) — bulk reading goes to a subagent whose transcript is separate; ranged reads beat whole-file reads; defer big reads to the step that needs them; batch independent tool calls into one step.

## Do this

Two moves, same session. (1) Measure your always-loaded surface — every file the agent reads at session start — and write the per-file token estimate down. (2) Take the largest habitual early read in your sessions and move it: to a subagent that returns a summary, to a ranged read, or later in the session.

Move 1 should end with a written list, one line per file read at session start, with a token estimate beside each. To check move 2, start a fresh session and look at its first few steps. The read you moved should no longer appear there in full.

**Done-check:** you can name your three most expensive always-loaded sources with numbers, and one habitual read has demonstrably moved (the session start no longer contains it).

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

[`ghost_token_counter.py`](../samples/scripts/ghost_token_counter.py) is the per-source baseline with history; [`token_report.py`](../samples/scripts/token_report.py) reads real spend per session. The [context carry-cost calculator](https://jamesross.ai/tools/context-cost?utm_source=github&utm_medium=repo&utm_campaign=learn-track) prices a read by position if you want the intuition before the instrument.

`ghost_token_counter.py baseline` prints a total and a breakdown with one row per source, each carrying an approximate token count. `token_report.py report` prints a row per day with API-equivalent dollars and a cache hit rate. The calculator prices one read twice, at the turn you set and near the end of the session, and shows the multiplier between them.

## If it didn't work

- The counter stops on a path error, or prints 0 for a source. The sample ships with a `<workspace>` placeholder as its root, and it reports zero for any path it can't find. Set `ROOT` and the memory directory to your own paths before the first run.
- The total looks lower than your runtime's own context figure. The counter estimates at four characters a token and leaves out MCP tool descriptions. Trust it for week-on-week comparison only.
- `token_report.py` fails before it prints a table. It calls `ccusage` through `npx`, so check that `npx` runs in your shell.
- The read you moved is back at session start. Something still asks for it there, so search your instruction files and any session-start skill or hook for the file's name.

---

*Next: [M3. Verification & oversight](03-verification-oversight.md) · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
