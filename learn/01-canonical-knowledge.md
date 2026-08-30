# M1. Canonical knowledge — one source of truth

> [Learn track](README.md) · dimension: **Canonical knowledge** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

The failure this module prevents is quiet: the same rule written in three files, all correct on the day they were written, one edited later. An agent loading all three now reads two versions and silently picks one. Nothing breaks. You just get a wrong answer months later with no obvious cause.

The fix is structural, not disciplinary. Every fact gets exactly one canonical home; everything else points at it and says it's a pointer. A pointer can go stale, but stale-and-broken is loud. A copy that drifts is quiet, and quiet is the enemy.

## The patterns

- [**Pattern 1. Pure roles, composed with project facts**](../PATTERNS.md#1-pure-roles-composed-with-project-facts) — expert personas hold method with zero entity facts; project specifics live in a `CONTEXT.md`; a thin binding composes the two. A fix to the role reaches every project at once.
- [**Pattern 5. Memory points, it doesn't mirror**](../PATTERNS.md#5-memory-points-it-doesnt-mirror) — agent memory holds an index and typed notes that point at sources of truth. A pointer cannot contradict its source; a copy eventually always does.
- [**Pattern 17. One canonical copy, and pointers from everywhere else**](../PATTERNS.md#17-one-canonical-copy-and-pointers-from-everywhere-else) — the same instinct applied to instruction files, where duplication costs tokens on every session *and* drifts.

## Do this

Find one rule that exists in two of your instruction files (a communication preference, a git convention, a formatting rule — grep a distinctive phrase from your main instruction file across the rest). Pick the canonical home. Reduce the other instance to a one-line pointer naming the file and section — a reference, not a summary, because a summary is a copy that drifts more slowly.

**Done-check:** the phrase now greps to exactly one file plus pointers, and the pointer names its target explicitly.

## Measure it

[`claudemd_audit.py`](../samples/scripts/claudemd_audit.py) inventories every always-loaded instruction file and flags cross-file duplicated boilerplate. Run it before and after; the duplication count should drop by at least one.

Next: [M2. Context economics](02-context-economics.md) — what the duplicated copy was costing you per session.
