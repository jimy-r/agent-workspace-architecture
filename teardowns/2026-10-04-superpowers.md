# Teardown: Superpowers

- **Subject:** https://github.com/obra/superpowers
- **Revision read:** `8ca22dba9a94` (main, 2026-09-25, release v6.4.2); surfaces read: the fifteen skills under `skills/`, `hooks/`, the harness ports, `tests/`, `README.md`, `AGENTS.md`, `RELEASE-NOTES.md`, `docs/testing.md`, and the specs and plans under `docs/superpowers/` (the most recent in full, the older ones skimmed). The eval harness lives in a separate repository and was not read. Verdicts stop at the files named. Nothing was installed or run.
- **Patterns present:** [10](../PATTERNS.md#10-a-skill-is-editable-weights--never-adopt-a-self-edit-without-a-gate), [11](../PATTERNS.md#11-a-scaffold-is-a-hypothesis--gate-it-behind-a-measurable-signal), [15](../PATTERNS.md#15-price-the-lane-before-you-migrate-it), [18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it) ([3](../PATTERNS.md#3-make-silent-failure-loud-the-dead-mans-switch), [7](../PATTERNS.md#7-a-cheap-hook-beats-a-careful-agent), [9](../PATTERNS.md#9-context-is-a-budget-not-a-constant), [16](../PATTERNS.md#16-a-claim-carries-its-provenance-or-it-is-a-guess) and [17](../PATTERNS.md#17-one-canonical-copy-and-pointers-from-everywhere-else) partial)
- **Patterns absent worth noting:** [8](../PATTERNS.md#8-audit-the-workspace-like-a-fitness-function)
- **Date:** 2026-10-04
- **Status:** current <!-- as at 2026-10-04 -->
- **Re-check by:** 2027-04-04
- **Verified:** 2026-10-04, 56 citations re-read
- **Maintainer heads-up:** not sent (rule 4)

## What it is

Superpowers is Jesse Vincent's skills library and working method for coding agents. It is MIT-licensed, and its README gives install steps for sixteen harnesses that all read one `skills/` tree. Fifteen skills carry the work from brainstorming to a spec, a plan, test-first implementation by subagents, review and a finished branch. This page reads release v6.4.2 and spends most of its time in `docs/superpowers/`, where the project keeps the specs and plans for changes to itself.

## What works

**A rule is not written until a control shows the failure (pattern [11](../PATTERNS.md#11-a-scaffold-is-a-hypothesis--gate-it-behind-a-measurable-signal)).** The authoring guide tells a skill writer to test wording with "5+ reps per variant", because "Single samples lie", and to "Always include a no-guidance control. If the control doesn't exhibit the failure, there is nothing to fix" (`skills/writing-skills/SKILL.md`). The project followed its own rule. A June spec proposed relocating a banned-patterns list in the planning skill, ran the test first, and found "0 placeholders in all 20 plans across all four variants including the no-guidance control", then 40 of 40 clean under pressure. Its disposition was to leave the section as it was and "do NOT open the follow-up PR" (`docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md`).

**The form of an instruction is matched to the failure, with numbers.** The same spec measured how phrasing changed what a controller re-typed into a dispatch. A prohibition scored 4.4 spec values re-typed against 3.6 with no guidance at all, and a positive recipe scored 3.0 with zero variance. The authoring guide now carries that result as a table. Prohibitions and rationalisation tables are for an agent that "knows better, does it anyway". Output of the wrong shape gets a recipe, and an omitted element gets a required slot.

**Lanes are priced, and failed experiments stay on the record (pattern [15](../PATTERNS.md#15-price-the-lane-before-you-migrate-it)).** The cost spec opens with where the dollars go in a run of about $13, by component (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md`). Its quality gate is a planted-defect pass rate over five runs, with the note that "single-run gates were this campaign's weakest methodology". Two cheaper tiers were tried against that gate. The controller tier "DIED AT THE GATES, as pre-registered". The reviewer tier is marked "DEAD, as pre-registered" after forced-haiku reviewers passed 2 of 5 against a baseline of 5 of 5, and its status note ends "Do not re-propose without a structurally different design."

An eval record in the same folder is as plain about itself. It reports that the failure it set out to show "did not reproduce", that the tool-call count "did **not** drop (9.6 vs 9.0)", and that "Five reps per cell is a smoke-strength signal, not a statistical one" (`2026-07-06-sdd-plan-scoped-workspace-eval-results.md`).

**Context cost is stated the way I'd state it (pattern [18](../PATTERNS.md#18-position-is-price--a-token-costs-more-the-earlier-you-add-it)).** "Every tool call is a turn that re-reads your whole context" (`skills/executing-plans/SKILL.md`), so bookkeeping is told to ride along with work. The always-loaded surface is one file of 3,192 bytes, `skills/using-superpowers/SKILL.md`, which the session-start hook injects. Every other skill loads when called.

**Changes to skill text pass a gate (pattern [10](../PATTERNS.md#10-a-skill-is-editable-weights--never-adopt-a-self-edit-without-a-gate)).** `AGENTS.md` says a pull request that rewords skills to match Anthropic's guidance "will not be accepted without extensive eval evidence showing the change improves outcomes", and that "A human must review the complete proposed diff before submission." The diagnosing skill reads a user's transcripts under the rule "No citation, no finding" and is barred from the conclusion. "Never name a defect in a skill or propose a change" (`skills/diagnosing-superpowers/SKILL.md`). The harvest and the proposal sit on opposite sides of a person.

## The trade-offs

**The measurements live somewhere else (pattern [16](../PATTERNS.md#16-a-claim-carries-its-provenance-or-it-is-a-guess), partial).** `.gitignore` excludes `evals/` because the "Eval harness lives in its own repository", and the release notes give the reason. The submodule "broke plugin installs for some users". That is a fair trade for an installable plugin, and the cost falls on anyone checking a claim. v6.4.2 says its new plans "executed 9/9 against planted-defect probes on Sonnet 5", and `docs/superpowers/` holds no spec or plan dated after August. The cost spec cites an "experiments log" that is not in the tree. The v6.0.0 note reports results "roughly twice as fast" on "almost 50% fewer tokens". The nearest record in the tree, the spec for the review dispatch redesign, shows 54.1 to 54.7 minutes against a baseline of 64.9 on one scenario and "typical mid-band savings ~20-25%". Both can be true against different baselines, and a reader of the tree can't tell.

**Nothing in the tree runs the tests.** There are 66 files under `tests/` and no workflow to call them. `.github/` holds issue and pull request templates and a funding file. `package.json` defines no scripts. The three pre-commit hooks match only `^evals/.*\.py$`, a path the repository ignores. `tests/opencode/test-tools.sh` exits 0 when OpenCode isn't installed.

**A failed bootstrap looks like a working install (pattern [3](../PATTERNS.md#3-make-silent-failure-loud-the-dead-mans-switch), partial).** The session-start script reads the skill with `|| echo "Error reading using-superpowers skill"`, so a missing file injects that sentence as the skill and the script still ends `exit 0`. The Windows wrapper, on finding no bash, runs `exit /b 0` under the comment "exit silently rather than error" (`hooks/run-hook.cmd`). The Pi extension catches the error and returns null. The Hermes port does the opposite and says why. Its loader raises, because "a bootstrap that silently skips is how a broken install masquerades as a working one" (`.hermes-plugin/__init__.py`). The bug template records that the Windows hook "alone has been reported 29 times".

**The size targets are not met (pattern [9](../PATTERNS.md#9-context-is-a-budget-not-a-constant), partial).** The authoring guide sets under 150 words for getting-started workflows, under 200 for frequently loaded skills and under 500 for the rest. By `wc -w`, 13 of the 15 `SKILL.md` files pass 500 words, the injected one is 492, and `subagent-driven-development` is 4,873. The only word budget I found in a test is `WORD_BUDGET=1000`, for the diagnosing skill.

**Most controls are sentences, and sentences drift (patterns [7](../PATTERNS.md#7-a-cheap-hook-beats-a-careful-agent) and [17](../PATTERNS.md#17-one-canonical-copy-and-pointers-from-everywhere-else), partial).** The controller is told "Rulings, not stalls. A running plan does not wait on a human", while the reviewer template beside it still ends "the human decides" (`task-reviewer-prompt.md`). The README still describes plans with "complete code" and tasks of "2-5 minutes each", which the release notes in the same commit say were replaced. The OpenCode port shows the alternative. Its comment says the prose stop for subagents "relies on model compliance, which is not reliable", and the port skips the bootstrap for any session that has a `parentID`.

## What's conspicuously absent

**A recurring audit (pattern [8](../PATTERNS.md#8-audit-the-workspace-like-a-fitness-function)).** The tree has the parts an audit would run, among them structure tests and a word budget. Nothing runs them on a cadence or on a pull request, and nothing compares the README or the reviewer template with the skills they describe. The drift above is the kind an audit finds in its first pass.

## What this teaches

Run the control before you write the rule. It costs a handful of short runs, and it is the one step here that can tell you a rule is unnecessary. The second lesson is about where evidence lives. Superpowers measures more carefully than any other subject on these pages, and most of the numbers in its release notes still can't be traced from the published tree. If a number carries a claim, ship the record beside the note that cites it.

**What changed here:** My role pressure test gained a control arm on 2026-10-04, and a fault test borrowed from this reading found my own session hook failing quietly.

I have taken from Superpowers since April 2026. From that month the workspace adapted its debugging, verification and parallel-dispatch skills, its subagent review loop and a one-scenario version of its skill pressure test ([ATTRIBUTION](../ATTRIBUTION.md)). It added the v6.0 and v6.2 review controls to that loop over June and July, then cut the loop on 2026-09-23, because the lifted skill had never been run. In September it took the plan's spec pointer and the `Review Focus` line, which is on trial until 2026-11-23.

Two things changed with this reading. The pressure test ran one sample and answered every failure by strengthening "YOU MUST" wording. It now runs a control beside each scenario, without the role's guardrails, classifies the failure before any wording changes, and repeats three times before a change is adopted. The [sample](../samples/.claude/skills/role-pressure-test/SKILL.md) changed in the same pull request as this page. Then I ran the bootstrap fault against my own hook. With its source file missing, the hook that re-injects my lessons index after a compaction printed its header and nothing else, and exited 0. A guard that prints a failure line is written and tested on a copy. Both are in this repo's [CHANGELOG](../CHANGELOG.md) entry for 2026-10-04.

| Lift | Owner | Status | Re-check by |
|---|---|---|---|
| A control run, failure classification and three repeats in the role pressure test | maintainer | done | 2026-12-18 |
| A fail-loud guard in the lessons re-injection hook, after the fault test | maintainer | open | 2026-11-04 |
| Compliance-pressure wording as a default device, which the subject's own data argues against for shape problems | maintainer | declined | n/a |
| Decision-only plans (v6.4.2), until execution cost is published | maintainer | declined | n/a |
| Installing the plugin. The workspace lifts patterns and installs nothing | maintainer | declined | n/a |

---

*Found by a direct read: the repository was reviewed at this revision for patterns worth lifting, and its own design record turned out to be the strongest part. Conventions: [teardowns/README.md](README.md). Corrections welcome and will be appended, dated.*

*Next: [Zenith](2026-10-03-zenith.md), the previous teardown · All teardowns: [index](README.md) · Questions: [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · Patterns adapted to your stack: [jamesross.ai](https://jamesross.ai/?utm_source=github&utm_medium=teardown&utm_campaign=flagship) · New teardowns and patterns: [Agent Workspaces](https://jimyr.substack.com)*
