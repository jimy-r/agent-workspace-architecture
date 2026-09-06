---
name: verify-completion
description: Use when completing an implementation task, fixing a bug, or claiming that tests, build or lint pass. Proves the claim only - never investigates (systematic-debugging), never drives a browser (browse), never files the result (wrap).
---

## Iron Law

**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

If you have not run the verification command in this message, you cannot claim it passes. No exceptions.

## Gate Function

Before claiming any task is complete or any check passes:

1. **IDENTIFY** — What command proves this claim? (test runner, build, linter, original symptom reproduction)
2. **RUN** — Execute the full command now, in this message.
3. **READ** — Read the complete output. Check exit code. Count failures.
4. **VERIFY** — Does the output actually confirm the claim?
   - If NO: state the actual status with evidence.
   - If YES: state the claim with the evidence.
5. **CLAIM** — Only now may you say it passes.

Skipping any step means the claim is unverified.

## Common Failures

| Claim | Required Evidence | NOT Evidence |
|---|---|---|
| Tests pass | Test runner output showing 0 failures | "Should pass", previous run, "I'm confident" |
| Linter clean | Linter output with 0 warnings/errors | Extrapolation from reading the code |
| Build succeeds | Build command output with exit code 0 | "No obvious errors", linter passing |
| Bug fixed | Original symptom no longer reproduces | "The fix addresses the root cause" |
| Requirements met | Line-by-line checklist against spec | "All requirements handled" |
| UI/frontend works | Feature exercised in a real browser (render, interaction, console) | Type-checks and tests — they verify code correctness, not feature correctness |
| A container passes (suite, batch, folder, fleet) | Per-member enumeration naming the probe that covered each member | The container's aggregate result quoted as evidence for a specific member |
| Fixed/stable over time | Evidence captured when the failure can exist (cache expired, next scheduled fire, cold start) | A warm-cache or T+0 probe of a failure that needs time to manifest |

## Rationalization Table

| If you think... | Then... |
|---|---|
| "Should work now" | RUN the verification. |
| "I'm confident" | Confidence is not evidence. |
| "Partial check is enough" | Partial proves nothing about the rest. |
| "Agent said success" | Verify independently. |
| "I already checked earlier" | State changes. Re-verify now. |
| "There's no test suite" | Say so explicitly. Do not claim success. |
| "I verified the container" | Enumerate the members. A passing whole is not evidence for any given part. |

## Evidence modality (two rules the table rows above encode)

1. **Evidence must span what the claim covers.** A container passing is never evidence for its members — name the enumeration probe. A claim about a UI needs browser evidence, not compiler evidence.
2. **Evidence must arrive when the failure can exist.** A probe taken before the cache expires, the scheduler fires, or the cold path runs proves nothing about the steady state.

*(Both rows are incident-derived — lifted from an external verification-gate doctrine that names the same failure modes.)*

## Rules

- Never claim completion without pasting or citing the verification output.
- If a verification command fails, that failure is the new priority.
- If you cannot run verification (no test suite, no build command), state that explicitly rather than claiming success.
- "Done" means verified. "Code written" is not "done".

## AI-debt sub-check (run when the task generated 20+ lines of code)

Verification confirms behavior works; it does not confirm the code is clean. Before claiming completion on a substantial change, scan the diff for:

- **Swallowed errors** — `catch (e) {}`, bare `except: pass`, or any handler that discards the error instead of logging or re-raising it.
- **Orphaned resources** — files, connections, or handles opened/created with no matching close/dispose, and no `finally` to guarantee it.
- **Hallucinated dependencies** — imports, API methods, or package names that don't exist; verify against the installed environment, not memory.
- **Unhandled edge cases** on the changed paths — empty input, null, off-by-one, the boundary the happy-path test doesn't hit.
- **Architectural drift** — does the new code match the surrounding file's existing patterns, or does it quietly introduce a different style/approach?

*Distilled from wshobson/agents ai-debt-detector.*
