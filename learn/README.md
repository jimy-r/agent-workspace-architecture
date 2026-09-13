# Learn the architecture

A guided track through the [patterns](../PATTERNS.md), organised around the six capabilities a governed agent workspace needs. Each module explains why one capability matters, points at the patterns that build it, and ends with an exercise you can complete in your own workspace the same day.

This is the *learning order*. [ADOPTION.md](../ADOPTION.md) is the *installation order* — what to set up first when you're standing up a workspace. The two differ because the thing worth understanding first (why claims need provenance) is rarely the thing worth installing first (a file-protection hook). Read here, install there.

## Where to start

Take the [workspace maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track) — 18 questions, scored across the same six dimensions as these modules. Your weakest dimension is your first module. No time for that? Start at [M0](00-foundations.md) and go in order.

If you'd rather build than read, take the hands-on companion track — [stand up a working workspace from the starter template](https://github.com/jimy-r/agent-workspace-starter/blob/main/docs/tutorial.md) — then come back here for the why.

## The modules

Every module is written to be entered cold. "Assumes" names what you need in place before the exercise works, not a module you must have finished. Times are read plus exercise, in one sitting.

| Module | Capability | Patterns | Time | Assumes | You will |
|---|---|---|---|---|---|
| [M0. Foundations](00-foundations.md) | the session loop | — | ~40 min | a folder and an agent runtime | run orient → plan → work → wrap once |
| [M1. Canonical knowledge](01-canonical-knowledge.md) | one source of truth | 1, 5, 17 | ~35 min | two or more instruction files to grep | collapse a duplicated rule into a canonical copy + pointers |
| [M2. Context economics](02-context-economics.md) | context as spend | 9, 18 | ~50 min | a session whose start-up reads you can list | measure your always-loaded surface; move one bulk read out |
| [M3. Verification & oversight](03-verification-oversight.md) | trust through checks | 8, 10, 11, 13 | ~65 min | one recurring prompt worth freezing as a case | write a golden case; register a scaffold with a review date |
| [M4. Safety & permissions](04-safety-permissions.md) | cheap mechanical guards | 4, 6, 7 | ~50 min | a scratch repo and a throwaway file to fire at | install two hooks and live-fire them on a safe target |
| [M5. Telemetry & cost](05-telemetry-cost.md) | loud failure, priced lanes | 3, 15 | ~50 min | one scheduled or recurring unattended task | put a dead-man's switch on one scheduled task |
| [M6. Provenance & delegation](06-provenance-delegation.md) | claims that carry sources; work that carries mandates | 2, 12, 14, 16 | ~50 min | a task file or board, and three tasks you might automate | run the four-box test; delegate one card properly |

Every pattern in [PATTERNS.md](../PATTERNS.md) appears in exactly one module and is cross-referenced where it touches others. The modules stay short on purpose: the patterns file carries the reasoning, the samples carry the implementation, and these pages carry the path through them.

## How each module works

**Read** the module page (five minutes). **Do** the exercise — most done-checks are mechanical rather than a "reflect on" prompt, and two are not: M2 asks you to name your three costliest always-loaded sources, which is a self-report, and M6 asks whether a delegated card's done-when is checkable by someone who did not write it, which needs a second reader. **Measure** with the named instrument, so you know the exercise took. **Record** the done-check somewhere outside your own head. A module without its exercise done is a module read, not learned.

## Track your progress

A done-check with no destination is a done-check nobody runs. Copy this into your own task file, or post it as one thread in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) and edit it as you go. Threads there are the closest thing this track has to a cohort: you can see what other people's workspaces scored, and where the same exercise broke differently.

```markdown
- [ ] M0 Foundations: loop run end to end, task file updated by the wrap
- [ ] M1 Canonical knowledge: duplicated phrase greps to one file plus pointers
- [ ] M2 Context economics: three costliest always-loaded sources named, one read moved
- [ ] M3 Verification & oversight: golden case written, scaffold row has a review date
- [ ] M4 Safety & permissions: two violations attempted, two blocks observed
- [ ] M5 Telemetry & cost: task killed deliberately, staleness flag surfaced
- [ ] M6 Provenance & delegation: three four-box verdicts written, one card delegated
```

Maturity-check scores from before and after the track are welcome in the same thread. The M0 baseline and the M6 retake are the track's own evidence that it moved anything.

## Questions and corrections

Questions, comparisons with your own setup, and half-finished exercises go to [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions), the canonical Q&A home, where answers stay findable for the next reader. Concrete defects go to [issues](https://github.com/jimy-r/agent-workspace-architecture/issues). If an exercise doesn't survive contact with your workspace, that's a defect in the exercise — report it.
