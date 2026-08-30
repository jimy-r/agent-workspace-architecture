# M3. Verification & oversight — trust through checks

> [Learn track](README.md) · dimension: **Verification & oversight** in the [maturity check](https://jamesross.ai/tools/maturity-check.html?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

An agent workspace accumulates two kinds of change nobody verifies by default: changes to the workspace (configs drift, hooks stop firing, memory contradicts reality) and changes *by* the workspace to itself (a better-worded skill, a folded-in lesson, a new reasoning rule). Both feel fine right up until they aren't. The shared discipline: nothing is adopted on the strength of how good it sounds. A change earns its place through a check that could have rejected it.

That cuts both ways. Most "make the agent smarter" additions — a second same-model pass, an always-on critic — never get checked either, and some degrade the result while costing tokens. The gate applies to the scaffolding you add, not just the edits the agent proposes.

## The patterns

- [**Pattern 8. Audit the workspace like a fitness function**](../PATTERNS.md#8-audit-the-workspace-like-a-fitness-function) — a scheduled auditor with canaries that prove it still detects known-bad fixtures, a finding ledger, and deliberately no single numeric score.
- [**Pattern 10. A skill is editable weights**](../PATTERNS.md#10-a-skill-is-editable-weights--never-adopt-a-self-edit-without-a-gate) — a proposed instruction edit is staged, reviewed, then adopted. The published cautionary case: an ungated self-edit loop collapsed its own benchmark score 0.554 → 0.026.
- [**Pattern 11. A scaffold is a hypothesis**](../PATTERNS.md#11-a-scaffold-is-a-hypothesis--gate-it-behind-a-measurable-signal) — register every capability addition with a falsifiable hypothesis and a review date; beat baseline or get cut. Removal is a first-class outcome.
- [**Pattern 13. Challenge half-formed ideas with a different lens**](../PATTERNS.md#13-challenge-half-formed-ideas-with-a-different-lens--and-hold-a-sample-back-to-prove-it-helps) — one grounded divergent challenge on real forks, with a held-out sample so the aid stays measurable.

## Do this

Two artefacts, an hour total. (1) Write one **golden case**: a prompt your workspace handles regularly, plus the deterministically checkable property a good answer must have (a file cited, a figure matched, a rule applied). (2) Pick one scaffold you've added — any always-loaded rule or skill — and write its register row: what it should improve, how that would be measured, and a review date at which it beats baseline or gets cut.

**Done-check:** both exist as files, and the register row's hypothesis is falsifiable — someone else could run the check and tell you the scaffold failed.

## Measure it

The audit machinery in [`samples/.claude/agents/audit.md`](../samples/.claude/agents/audit.md) shows the full shape: cadence, canaries, tiered findings. Your golden case is its seed — one case is a smoke test, twenty is a regression suite.

Next: [M4. Safety & permissions](04-safety-permissions.md).
