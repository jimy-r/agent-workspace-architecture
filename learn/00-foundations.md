# M0. Foundations — the session loop

> [Learn track](README.md) · start here, or wherever the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track) says you're weakest.

A governed agent workspace is an ordinary folder with three properties: the agent starts every session knowing where things stand, nothing important happens outside a recorded plan, and every correction you make becomes a rule the next session reads. None of that requires a framework. It requires files, a few skills, and the discipline to use them.

The unit of work is the **session loop**:

1. **Orient.** The agent reads a small fixed file set — active plan, task list, lessons, open questions — and briefs you: state, in-flight work, one recommended next action. Fixed set, because "look around and get up to speed" burns context on speculative reading and comes back with a different picture every time.
2. **Plan.** Work gets a checklist in a todo file before implementation starts. You approve the plan, not the diff.
3. **Work.** The agent executes, marking items as they complete.
4. **Wrap.** Completed work is integrated everywhere it belongs — task list updated, lessons captured, registries swept — instead of left in the diff for future archaeology.

The loop is small enough to feel bureaucratic on day one. It stops feeling that way the first time a session picks up exactly where the last one stopped, or the first time the agent declines to repeat a mistake because the correction was written down.

## Do this

Run the loop once end to end. Either in your own workspace (any folder with a `CLAUDE.md` and a task file will do) or by scaffolding the [starter template](https://github.com/jimy-r/agent-workspace-starter?utm_source=github&utm_medium=repo&utm_campaign=learn-track), which ships orient, tasks, and wrap as working skills.

**Done-check:** your task file shows one item added and struck through, and the session ended with a wrap that updated it — not with a summary in chat that no file records.

## Measure it

Take the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track) and keep the six-dimension result. It's the baseline the rest of the track moves.

Next: [M1. Canonical knowledge](01-canonical-knowledge.md), or jump to your weakest dimension.
