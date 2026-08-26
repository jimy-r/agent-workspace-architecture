# Evaluation: knowing whether a workspace change helped

A workspace that keeps adding skills, rules and always-loaded directives needs a way to tell which ones actually help. Without one, the surface only grows: every addition sounds reasonable at the moment it is proposed, nothing is ever removed, and the accumulated bloat suppresses the capability the additions were meant to raise.

This is the method used here. It is deliberately unfashionable in three places, and those three are the whole contribution.

## The instrument

A golden set of frozen cases, each replayed headless several times, reported as a pass-rate with variance, and trended over time.

Every case is one already-burned failure mode. Not a hypothetical, not a capability probe. A thing that went wrong, was recorded, and is now a regression test. Each case carries a `source` field naming the failure record it was frozen from, so the suite is the failure library turned executable.

That constraint does most of the work. A case you can point at a real incident is a case you can defend keeping. A case invented to look thorough is a case nobody can decide to delete.

## Three deliberate choices

### 1. Deterministic checks only, never a judge

Checks are regex, exact-value and path-existence. There is no LLM grading anywhere in the harness.

The reason is narrow and it matters: **this instrument exists to detect regression over time.** A judge introduces its own variance between runs, so a drop in the score becomes ambiguous. Did the workspace get worse, or did the judge? For a trend line, that ambiguity is fatal. A deterministic check drops only when behaviour actually changed.

This is not a claim that judges are useless. A judge is the right tool for open-ended quality where no deterministic check exists, and there is a place for one in a decision harness. It is the wrong tool for a regression trend, and conflating the two is common.

The check types that carry the most weight here, in rough order:

| Check | Catches |
|---|---|
| `must_cite_path` | An answer about system state given without a concrete file path |
| `no_fabricated_path` | A confidently-asserted path that does not exist on disk |
| `uncertainty_tag` | A knowable-unknown answered with a number instead of "cannot be known" |
| `must_not_contain` | A specific fabrication shape, expressed as a pattern |
| `must_contain` / `exact_value` | The correct answer, where one exists |

The first three are the ones worth stealing. They test *process* rather than *answer*, which is what makes them survive a model upgrade.

### 2. A pass-rate with variance, never a single number

Every case runs K times (default 5) and the suite reports a rate plus standard deviation.

LLM output is stochastic. A single run comparing before and after is noise presented as signal, and it will confidently tell you a change helped when it did nothing. Any measurement certifying a change here runs K≥3 and reports the spread.

The practical consequence is that a small improvement is often not measurable, and the honest response is to say so rather than shipping the change on a one-run delta.

### 3. Five fixture classes, and two of them are the point

Three passing positive cases prove very little. The value is in the classes that catch a check which looks right and is not.

| Class | What it proves |
|---|---|
| **Positive** | The behaviour happens when it should |
| **Negative** | The check fires when the behaviour is absent |
| **Lucky-correct negative** | Right answer, wrong process. Catches a check that passes on the answer while the reasoning was unsound |
| **Outside-scope** | The check does *not* fire on an unrelated case. Catches a check that passes everything |
| **Allowed boundary** | The edge case that should pass, so the check is not over-tight |

The lucky-correct negative and the outside-scope case are the two most often skipped and the two that actually validate the instrument. A check that has never been shown to fail on anything is not a check.

Every case also carries a `dry_fixture`: a model answer that should pass every check. This lets the checks themselves be validated for free, with no model calls, before the case joins the suite.

## What it costs

Real friction, and worth stating plainly.

Authoring is slow. A case needs a self-contained prompt, deterministic checks, a dry fixture, and a walk through the five classes. Fifteen minutes each is optimistic.

K=5 replay is five times the tokens of a single pass, which puts the full suite in the range where you run it at audit time rather than per change.

Deterministic checks cannot see quality. They catch fabrication, missing citation and false certainty. They say nothing about whether an answer was *good*, and a suite that stays green while the work degrades is a real possibility. This measures a floor, not a ceiling.

And the suite decays. Cases frozen from failures a model no longer makes become tests that always pass, which cost tokens and prove nothing. They need pruning on the same discipline as anything else here.

## How it connects to the rest

This is one half of a pair. The other is [`PATTERNS.md` #11](PATTERNS.md), which requires every capability scaffold to register a falsifiable hypothesis and a review date. The suite is what the review reads. Without the instrument, the review date arrives and the decision falls back to whether the scaffold still sounds like a good idea, which is how surfaces grow forever.

It also sits behind [`PATTERNS.md` #10](PATTERNS.md): a self-edit gate certifies a change to the instructions the way a correctness signal certifies a change to the capability layer. Both refuse to adopt on the strength of how good the change sounds.

**One failure worth carrying.** An all-zero record once appeared in the trend store and read as a total regression. It was a real run whose every call had failed on a dead credential. The fix was structural rather than a re-run: the harness now counts call outcomes and self-marks invalid runs, and the trend check filters on that dedicated field. **An outage has to be distinguishable from a regression by the record itself**, or the instrument will eventually lie to you in the most alarming direction available.

## Where it lives

- [`samples/scripts/reasoning_golden_run.py`](samples/scripts/reasoning_golden_run.py) carries the harness: case loading, K-replay, the check evaluators, the history record, and a free self-test
- [`samples/tests/reasoning_golden/README.md`](samples/tests/reasoning_golden/README.md) is the authoring guide, including the full case schema
- [`samples/tests/reasoning_golden/cases/`](samples/tests/reasoning_golden/cases/) holds three representative cases, one per transferable check family

The corpus itself is not published. Cases encode workspace-specific paths and internal failures, so the method transfers and the corpus does not. Build your own from your own recorded failures. That is the point of the `source` field, and a suite inherited from someone else's incidents tests the wrong things.
