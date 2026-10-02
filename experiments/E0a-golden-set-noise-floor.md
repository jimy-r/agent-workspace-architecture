# E0a. The golden set's noise floor

- **Question:** What is the smallest change in the golden set's composite pass rate that it can detect between two configurations?
- **Registered:** 2026-09-27, before any analysis ran
- **Protocol hash:** none. Hashing began with E2, so this protocol was dated before the data but not hashed.
- **Run:** 2026-09-27 to 2026-09-28, two full replays of 89 cases at k=3
- **Data and code:** the 89 active golden-set cases described in [EVALUATION.md](../EVALUATION.md), run by the workspace's private golden-set runner, which is not published.
- **Model and engine:** `claude-opus-5-5` at effort `max`, the runner's defaults. The Claude Code engine version was not recorded.
- **Status:** Adopted, because the golden-set regression check was rebased on the floor this experiment measured.

## Why it ran

The [golden set](../EVALUATION.md) is the workspace's quality guard. It replays frozen cases k times each and reports a pass rate, and every later experiment that claims "no quality loss" leans on it. A drop smaller than the set's noise floor is invisible, however carefully the experiment around it is run. So the first job was to measure that floor.

## Hypotheses

| # | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| H1 | Paired analysis brings the minimum detectable effect (MDE) low enough to guard fine changes | MDE at or below 0.05 at k=3 | FAIL (0.071) |
| H2 | Two runs of one unchanged configuration agree | the 95% interval of their mean difference contains zero | PASS |
| H3 | The analytic floor predicts the measured one | within a factor of 1.5 | PASS (1.32) |

The decision rules were fixed before the runs.

- If H1 fails with the floor at or below 0.10, the result reports the k that would reach 0.05.
- If the floor is above 0.10, the golden set can't guard fine-grained changes, and judged task replay becomes the main quality guard.
- If H2 fails, no experiment uses the golden set as its guard until the cause is found.

## Method

The first step made no model calls. It predicted the standard error of a paired A/A difference from the per-case pass rates of the previous full run, as SE = √(Σ 2·pᵢ(1 − pᵢ) / k) / n, and set the MDE at 2.8 × SE (80% power, two-sided α of 0.05).

The second step ran the unchanged configuration twice, 89 cases at k=3 each, at the runner's default model and effort. For each case it took the difference in pass rate between the two runs. It then bootstrapped the mean difference over cases, 10,000 resamples with a fixed seed, for a 95% interval. The measured MDE is 2.8 times the bootstrap standard error.

Pairing matters here. Each case is compared with itself, which takes the spread between cases out of the comparison. An unpaired comparison of the same set, estimated from that spread, needs a difference of about 0.17 before it shows.

## Results

| Measure | Run A | Run B |
|---|---|---|
| Composite pass rate | 0.772 | 0.802 |
| Standard deviation across cases | 0.345 | 0.311 |
| Calls that succeeded / timed out | 266 / 1 | 265 / 2 |
| Wall time | 5 h 12 min | 5 h 20 min |
| Cost, API list-price equivalent | $142.03 | $139.77 |

| Paired comparison, B minus A | Value |
|---|---|
| Cases | 89 |
| Mean difference | +0.030 |
| Bootstrap 95% interval | −0.019 to +0.079 |
| Bootstrap standard error | 0.0253 |
| Measured MDE (2.8 × SE) | 0.071 |
| Analytic MDE from the first step | 0.054 |
| Measured over analytic | 1.32 |
| k that would bring the MDE to 0.05 | 7 (6.03 before rounding up) |
| Cases whose pass rate differed between the two runs | 30 of 89 |
| Cost per successful call | about $0.53 |

## Verdicts

- **H1: FAIL.** The measured MDE is 0.071 at k=3, above the 0.05 target. The floor sits below 0.10, so the decision rule applies. At k=7 the floor would reach 0.05. By the same 1/√k scaling, the published harness's default of k=5 would detect about 0.055.
- **H2: PASS.** The interval for the A/A difference, −0.019 to +0.079, contains zero.
- **H3: PASS.** The measured floor is 1.32 times the analytic one, inside the factor of 1.5.

## Limits the record reports

Both runs started within a second of each other and shared one window. The floor is therefore the noise between two runs inside a single window, and the paired test registered for [E5](E5-standing-surface.md) starts both of its arms in one window too.

Three calls timed out after 240 seconds and were retried, one in run A and two in run B. And the first step's input came from a record made before 27 cases were rewritten, so its figure was only ever a pre-estimate.

## What changed here

The golden-set regression check was rebased on this floor. It now pairs the two latest real records case by case and flags a drop only when the paired bootstrap 95% interval sits wholly below zero. On the history as it stood, the check passes at +0.030.

The measured MDE of 0.071 also became the non-inferiority margin for the reasoning test in [E5](E5-standing-surface.md). And a full run now has a price. At API list rates, 89 cases at k=3 cost about $140.

---

*[All experiments](README.md) · Next, [E1. Cache economics](E1-cache-economics.md) · [Questions and disagreements in Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions)*
