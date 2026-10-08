# M1. Canonical knowledge — one source of truth

> [Learn track](README.md) · dimension: **Canonical knowledge** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can take a rule that lives in two instruction files and leave it in one, with a grep to prove it.

The failure this module prevents is quiet: the same rule written in three files, all correct on the day they were written, one edited later. An agent loading all three now reads two versions and silently picks one. Nothing breaks. You just get a wrong answer months later with no obvious cause.

The fix is structural, not disciplinary. Every fact gets exactly one canonical home; everything else points at it and says it's a pointer. A pointer can go stale, but stale-and-broken is loud. A copy that drifts is quiet, and quiet is the enemy.

## The patterns

- [**Pattern 1. Pure roles, composed with project facts**](../PATTERNS.md#p1) — expert personas hold method with zero entity facts; project specifics live in a `CONTEXT.md`; a thin binding composes the two. A fix to the role reaches every project at once.
- [**Pattern 5. Memory points, it doesn't mirror**](../PATTERNS.md#p5) — agent memory holds an index and typed notes that point at sources of truth. A pointer cannot contradict its source; a copy eventually always does.
- [**Pattern 17. One canonical copy, and pointers from everywhere else**](../PATTERNS.md#p17) — the same instinct applied to instruction files, where duplication costs tokens on every session *and* drifts.

## Do this

Find one rule that exists in two of your instruction files (a communication preference, a git convention, a formatting rule — grep a distinctive phrase from your main instruction file across the rest). Pick the canonical home. Reduce the other instance to a one-line pointer naming the file and section — a reference, not a summary, because a summary is a copy that drifts more slowly.

Run the same grep before and after the edit. The first run should list at least two files. The second should list the canonical home alone, with a one-line reference standing where the other copy was.

**Done-check:** the phrase now greps to exactly one file plus pointers, and the pointer names its target explicitly.

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

[`claudemd_audit.py`](../samples/scripts/claudemd_audit.py) inventories every always-loaded instruction file and flags cross-file duplicated boilerplate. Run it before and after; the duplication count should drop by at least one.

The script prints an inventory of the `CLAUDE.md` files it found. When lines repeat across them it adds a `CROSS-FILE DUPLICATION` block that opens with a count, and that count is the figure to compare between runs. With nothing left to report, the block is absent.

## If it didn't work

- The grep still lists two files. Read the pointer you wrote. If it repeats or paraphrases the rule it is still a copy, so cut it back to the file and section name. Then look for a third copy you hadn't found.
- The audit's count didn't move. The script reads only files named `CLAUDE.md`, including the user-global one. It counts only lines of 40 characters or more that match exactly. A copy in a differently named file never registers, and neither does a short or reworded one. Your grep is the check for those.
- The inventory is empty or lists the wrong files. The script finds the workspace from its own location, one folder above the directory it sits in, so keep it in a `scripts/` folder at the workspace root.

---

*Next: [M2. Context economics](02-context-economics.md), what the duplicated copy was costing you per session · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
