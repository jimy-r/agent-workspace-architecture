> **Sample.** This is the authoring guide from the source workspace, paths genericised. The method it
> describes is documented in [`EVALUATION.md`](../../../EVALUATION.md); this file is the working reference
> for adding a case. The 89-case corpus itself is not published: cases encode workspace-specific paths and
> internal failures, so the method transfers and the corpus does not.

# Golden-set reasoning cases — authoring guide

Each file in `cases/` freezes one already-burned failure mode from `tasks/lessons.md` as a self-contained prompt with deterministic checks. The harness is `scripts/reasoning_golden_run.py`; it replays every case K times (default 5) for a pass-*rate* plus stddev, and appends one record per run to `scripts/_state/reasoning_history.jsonl`. Checks are regex and path-existence only, never an LLM judge, so a drop in the rate is a real regression rather than judge noise.

```
python scripts/reasoning_golden_run.py run --dry --no-write   # free self-test against dry_fixture
python scripts/reasoning_golden_run.py run --k 5 --model opus # real replay
python scripts/reasoning_golden_run.py selftest               # free: record shape + audit compatibility
```

## Case schema

One JSON object per file in `cases/`, filename stem matching `id`.

| Field | Purpose |
|---|---|
| `id` | Stable case identifier. Used as the per-case key in the history record. |
| `source` | The `lessons.md` entry (date + title) or other failure record the case is frozen from. |
| `guards` | One line naming the failure mode this case catches, written as the behaviour to prevent. |
| `prompt` | The full prompt sent headless. Must carry its own context; the harness adds nothing. |
| `checks` | Array of deterministic checks. A run passes only if **every** check passes. |
| `dry_fixture` | A model answer that should pass every check. `--dry` evaluates the checks against this instead of calling Claude. |
| `arm_comparable` | Optional. `true` marks a case whose answer should be sensitive to the workspace context surface, so it is meaningful in an arm-vs-arm comparison. Absent means false. The runner records the count as `arm_comparable_cases`; it changes no score. |

Check types (`scripts/reasoning_golden_run.py`, `_EVALUATORS`): `must_contain`, `must_not_contain`, `exact_value`, `must_cite_path`, `uncertainty_tag`, `no_fabricated_path` (optional `allow` list for paths the prompt itself supplied).

## Fixture classes

Every new case family should walk these five classes and add the ones that apply. Three passing positives prove nothing on their own; the value is in the classes that catch a check which looks right and is not.

| Class | What it proves | How it looks here |
|---|---|---|
| **Positive** | The trigger fires and the required conduct is visible. | `must_contain` on the conduct the lesson demands. |
| **Negative** | The trigger fires and the required conduct is missing or contradicted. | `must_not_contain` on the shortcut phrasing the lesson was written against. |
| **Lucky-correct negative** | The right answer produced by the wrong process. **The class that catches outcome-only checks.** | Pair a check on the conclusion with a check on the step that earns it, so an answer that lands the conclusion without doing the work still fails. |
| **Outside-scope** | The trigger does not fire, so the guard should stay quiet. Proves the check does not false-positive. | A near-miss prompt where the rule genuinely does not apply, with `must_not_contain` on the refusal or hedge boilerplate. |
| **Allowed boundary** | A permitted alternative path is not scored as a failure. | Widen the `must_contain` alternation to accept the legitimate variant instead of pinning one phrasing. |

Change one boundary at a time between related cases. When two cases differ in several ways at once, a disagreement between them has no diagnosable cause.

## Comparison arms and directional defects

Every history record carries an `arm`, the label for the context configuration that produced it.

| Arm | What it means |
|---|---|
| `project-surface` (default) | The normal workspace-loaded configuration. The harness calls `claude --print --add-dir <workspace>` with cwd set to the workspace, so the project `CLAUDE.md` and `.claude/rules/` are in context. |
| `project-surface-off` | A comparison run with the project surface removed. Not yet wired as a harness mode. The label is reserved so the schema does not have to change when it is. |

No arm is bare, and none should be labelled that way. The user-global `~/.claude/CLAUDE.md` loads in every working directory, so its rules sit in every run whatever the label says. A real off-arm drops `--add-dir <workspace>` **and** runs from a scratch cwd outside the workspace. Do only one and the project surface is still loaded, so the two arms differ by cwd rather than by context, and the delta measures nothing you wanted.

Mark a case `arm_comparable: true` when its answer should move if the surface moves, because it turns on a workspace file, a rule, or a path. Cases that test general reasoning stay unmarked. A comparison averaged over unmarked cases pulls the measured difference toward zero and makes a real effect look like noise.

Before writing an off-arm record to the shared history, note that `check_reasoning_regression` in `scripts/audit_checks/run_all.py` compares the two most recent real records with no arm filter. An off-arm record therefore trends against a project-surface one, and the gap between arms reads as a model regression. The runner prints a warning whenever the arm is not the default. Until the check learns about arms, run off-arm with `--no-write` and keep those records in a separate file.

### Directional defects

When a harness bug turns up, record which arm it favoured before fixing it. A check that resolves paths relative to the workspace root passes more readily when the workspace is loaded, so it flatters `project-surface`. A fixture that leaks its expected string flatters whichever arm was used to write it. The fix removes the defect. The direction it leaned is what tells you whether results already collected under it were inflated or deflated, and which past comparisons have to be re-run. Write that direction into the commit message or the case's `source` field at the time of the fix. Recovering it later from a corrected harness is guesswork.

## Hygiene

- **Keep expected labels and case ids out of the evaluated prompt text.** The `prompt` field is everything the model sees. A case id, a class name, or a restatement of the expected answer leaks the answer, and the case then measures label recall rather than the reasoning it was written to test. Put that material in `id`, `source`, and `guards`, which the model never receives.
- **Do not make the negative case comically bad.** It should read like a plausible run that a competent model might actually produce. An obviously wrong negative passes trivially and certifies nothing about the boundary.

The five fixture classes and both hygiene rules are adapted from [braintrustdata/agentbehavior](https://github.com/braintrustdata/agentbehavior) (Apache-2.0), `references/calibrating-with-trajectories.md`.
