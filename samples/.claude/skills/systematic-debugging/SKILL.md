---
name: systematic-debugging
description: Use when investigating bugs, errors, test failures, or unexpected behavior that is not immediately obvious. Invoke via "debug this", "/systematic-debugging", "why is this failing". Investigates only - to prove a fix's tests/build/lint pass use verify-completion, to check a rendered page use browse.
---

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

If you have not completed Phase 1, you cannot propose fixes. Guessing wastes more time than investigating.

## Phase 1: Root Cause Investigation

1. **Read error messages carefully and completely.** Stack traces, line numbers, error codes. Do not skip past them.
2. **Reproduce the failure.** Confirm you can see it. If you cannot reproduce it, say so — do not fix what you cannot see.
3. **Check recent changes.** `git log`, `git diff`. What changed that could cause this?
4. **Gather evidence at component boundaries.** For multi-component systems, log what enters and exits each layer. Run once to identify WHERE it breaks before asking WHY.
5. **Trace data flow.** Follow the data from source to error. The bug is where the data diverges from expectation.

## Phase 2: Pattern Analysis

1. **Find a working example** of similar functionality in the codebase.
2. **Compare** the broken case against the working reference. Read references completely.
3. **Identify the specific difference** — this is your candidate root cause.

## Phase 3: Hypothesis Testing

1. **Form a single hypothesis** about the root cause.
2. **Design a minimal test** — change one variable at a time.
3. **Run the test and record the result.**
4. If disproved, return to Phase 1 with the new evidence. Do not stack hypotheses.

## Phase 4: Implementation

1. **Write a failing test** that reproduces the bug (if a test framework exists).
2. **Apply a single, targeted fix** addressing the root cause. One change at a time.
3. **Verify** the fix resolves the original symptom.
4. **Run the full test suite** to check for regressions.

## Escalation Rule

**If 3+ attempted fixes have failed: STOP.**

You are likely wrong about the root cause, or the problem is architectural. Do not attempt Fix #4. Instead:

- Summarise what you tried and what each attempt revealed.
- Present the evidence to the user.
- Ask whether to continue investigating or reconsider the architecture.

Signs of an architectural problem:
- Each fix reveals new issues in different places.
- Fixes require large-scale refactoring to implement.
- Each fix creates new symptoms elsewhere.

## Rules

- Never skip straight to a fix without completing Phase 1.
- One variable at a time in Phase 3.
- If you cannot reproduce the bug, say so. Do not fix what you cannot see.
- "I don't know" is a valid intermediate answer. Research, do not guess.
