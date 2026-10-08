# M3. Verification & oversight — trust through checks

> [Learn track](README.md) · dimension: **Verification & oversight** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can turn one recurring prompt into a case a script can mark pass or fail, and say what result would get one of your own scaffolds cut.

An agent workspace accumulates two kinds of change nobody verifies by default: changes to the workspace (configs drift, hooks stop firing, memory contradicts reality) and changes *by* the workspace to itself (a better-worded skill, a folded-in lesson, a new reasoning rule). Both feel fine right up until they aren't. The shared discipline: nothing is adopted on the strength of how good it sounds. A change earns its place through a check that could have rejected it.

That cuts both ways. Most "make the agent smarter" additions — a second same-model pass, an always-on critic — never get checked either, and some degrade the result while costing tokens. The gate applies to the scaffolding you add, not just the edits the agent proposes.

## The patterns

- [**Pattern 8. Audit the workspace like a fitness function**](../PATTERNS.md#p8) — a scheduled auditor with canaries that prove it still detects known-bad fixtures, a finding ledger, and deliberately no single numeric score.
- [**Pattern 10. A skill is editable weights**](../PATTERNS.md#p10) — a proposed instruction edit is staged, reviewed, then adopted. The published cautionary case: an ungated self-edit loop collapsed its own benchmark score 0.554 → 0.026.
- [**Pattern 11. A scaffold is a hypothesis**](../PATTERNS.md#p11) — register every capability addition with a falsifiable hypothesis and a review date; beat baseline or get cut. Removal is a first-class outcome.
- [**Pattern 13. Challenge half-formed ideas with a different lens**](../PATTERNS.md#p13) — one grounded divergent challenge on real forks, measured by the human's tag on each firing. A held-out sample was tried and dropped.

## Do this

Two artefacts, an hour total. (1) Write one **golden case**: a prompt your workspace handles regularly, plus the deterministically checkable property a good answer must have (a file cited, a figure matched, a rule applied). (2) Pick one scaffold you've added — any always-loaded rule or skill — and write its register row: what it should improve, how that would be measured, and a review date at which it beats baseline or gets cut.

The golden case should be a file holding the prompt and at least one check that no model has to judge. Test it by hand. An answer you know is good passes, and one you know is bad fails. The [sample cases](../samples/tests/reasoning_golden/cases/) keep such a known-good answer in a `dry_fixture` field. The register row should answer the three questions above, and its measurement should name a result that would count against the scaffold.

**Done-check:** both exist as files, and the register row's hypothesis is falsifiable — someone else could run the check and tell you the scaffold failed.

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

The audit machinery in [`samples/.claude/agents/audit.md`](../samples/.claude/agents/audit.md) shows the full shape: cadence, canaries, tiered findings. Your golden case is its seed — one case is a smoke test, twenty is a regression suite.

After reading the audit sample you should be able to point to its Phase 0, which checks the canary fixtures before any other phase runs, and to the table that sets a finding's tier from the file path and the kind of change.

## If it didn't work

- Your check needs a person or a model to judge it. Narrow the property until a string match or a path that must exist settles it. The sample cases do this with check types such as `must_contain` and `must_cite_path`.
- The check passes whatever the answer says. Write a plausible wrong answer and run the check against it. If both answers pass, the check is too loose to catch a regression.
- The prompt gives the answer away. The model sees the whole prompt, so keep expected strings and case names out of it.
- You can't say what would make the scaffold fail. The hypothesis isn't falsifiable yet. Restate it as a number that could drop or a check that could fail, and keep the review date.

---

*Next: [M4. Safety & permissions](04-safety-permissions.md) · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
