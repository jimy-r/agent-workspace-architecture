# Learn the architecture

A guided track through the [patterns](../PATTERNS.md), organised around the six capabilities a governed agent workspace needs. Each module explains why one capability matters, points at the patterns that build it, and ends with an exercise you can complete in your own workspace the same day.

This is the *learning order*. [ADOPTION.md](../ADOPTION.md) is the *installation order* — what to set up first when you're standing up a workspace. The two differ because the thing worth understanding first (why claims need provenance) is rarely the thing worth installing first (a file-protection hook). Read here, install there.

## Where to start

Take the [workspace maturity check](https://jamesross.ai/tools/maturity-check.html?utm_source=github&utm_medium=repo&utm_campaign=learn-track) — 18 questions, scored across the same six dimensions as these modules. Your weakest dimension is your first module. No time for that? Start at [M0](00-foundations.md) and go in order.

If you'd rather build than read, take the hands-on companion track — [stand up a working workspace from the starter template](https://github.com/jimy-r/agent-workspace-starter/blob/main/docs/tutorial.md) — then come back here for the why.

## The modules

| Module | Capability | Patterns | You will |
|---|---|---|---|
| [M0. Foundations](00-foundations.md) | the session loop | — | run orient → plan → work → wrap once |
| [M1. Canonical knowledge](01-canonical-knowledge.md) | one source of truth | 1, 5, 17 | collapse a duplicated rule into a canonical copy + pointers |
| [M2. Context economics](02-context-economics.md) | context as spend | 9, 18 | measure your always-loaded surface; move one bulk read out |
| [M3. Verification & oversight](03-verification-oversight.md) | trust through checks | 8, 10, 11, 13 | write a golden case; register a scaffold with a review date |
| [M4. Safety & permissions](04-safety-permissions.md) | cheap mechanical guards | 4, 6, 7 | install two hooks and live-fire them on a safe target |
| [M5. Telemetry & cost](05-telemetry-cost.md) | loud failure, priced lanes | 3, 15 | put a dead-man's switch on one scheduled task |
| [M6. Provenance & delegation](06-provenance-delegation.md) | claims that carry sources; work that carries mandates | 2, 12, 14, 16 | run the four-box test; delegate one card properly |

Every pattern in [PATTERNS.md](../PATTERNS.md) appears in exactly one module and is cross-referenced where it touches others. The modules stay short on purpose: the patterns file carries the reasoning, the samples carry the implementation, and these pages carry the path through them.

## How each module works

**Read** the module page (five minutes). **Do** the exercise — each has a done-check you can verify mechanically, not a "reflect on" prompt. **Measure** with the named instrument, so you know the exercise took. A module without its exercise done is a module read, not learned.

Questions and corrections go to [issues](https://github.com/jimy-r/agent-workspace-architecture/issues). If an exercise doesn't survive contact with your workspace, that's a defect in the exercise — report it.
