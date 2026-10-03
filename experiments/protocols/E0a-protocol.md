# E0a protocol, redacted copy

These are the Protocol, Hypotheses and Decision rules sections of [E0a. The golden set's noise floor](../E0a-golden-set-noise-floor.md), as registered on 2026-09-27 before the data they test was read.

**There is no hash to check this copy against.** Hashing began with E2, so E0a's protocol was dated before the data but not hashed.

Redaction made two kinds of change and nothing else. The user's name reads "the user". The line on how the runner authenticates is reworded in general terms. Workspace-relative paths, such as those under `scripts/`, name private files that aren't published, and are left as written. "The Result" means the result section of the private original, which the E0a page reports.

---

## Protocol

- **Question.** What is the smallest change in composite pass rate the golden set can detect between two configurations?
- **Instrument.** `scripts/reasoning_golden_run.py` on the 89 active cases in `tests/reasoning_golden/cases/`, at the runner defaults (model `claude-opus-5-5`, effort `max`) and k=3.
- **Step 1, analytic floor.** This step makes no model calls. It predicts the standard error of a paired A/A difference from the within-case binomial variance in the 2026-09-23 record's per-case rates, as SE = sqrt(Σ 2·p_i(1−p_i)/k) / n. The minimum detectable effect is 2.8 × SE (80% power, two-sided α = 0.05). The 27 cases rewritten on 2026-09-25 make this a pre-estimate only.
- **Step 2, A/A.** Two full runs of the unchanged configuration, arms `aa-1` and `aa-2`, each with `--no-write` and `--record-out` into `tasks/experiments/E0a/`. A new `compare` subcommand reports the paired per-case differences, their mean, a bootstrap 95% interval over cases (10,000 resamples, fixed seed) and the empirical minimum detectable effect (2.8 × bootstrap SE). Per-run cost and tokens come from the `--output-format json` envelope.
- **Why `--no-write`.** `check_reasoning_regression` compares the two latest records in `scripts/_state/reasoning_history.jsonl`. Whether this pair becomes the new baseline, as item 2 of `tests/reasoning_golden/dispositions-2026-09-25.md` anticipates, is the user's decision.
- **Credential.** The runner authenticates its headless child with the workspace's scheduled-task credential, which is how it was designed to run. No agent reads, prints, copies or moves that credential. Step 2 runs only under the user's ruling for the run.

## Hypotheses

- **H1.** Paired analysis gives a minimum detectable effect of 0.05 or less at k=3.
- **H2.** The 95% interval of the A/A mean difference contains zero. If it does not, something non-stationary is in the data, such as model drift, throttling or failed calls.
- **H3.** The analytic and empirical floors agree within a factor of 1.5.

## Decision rules

- If H1 fails but the floor is 0.10 or less, the Result gives the k that would reach 0.05, since the floor scales as 1/√k.
- If the floor is above 0.10, the golden set cannot guard fine-grained changes, and judged task replay becomes the program's main quality guard.
- If H2 fails, no efficiency experiment uses the golden set as its guard until the cause is found.

**Budget.** About 540 headless calls at the runner defaults. This experiment is the first to record what a run costs. Extra usage is off on the account, so the plan limit caps the spend.
