---
name: terse-mode
description: Use when the user says "terse", "/terse-mode", "terse mode", "compress output", or asks Claude to reduce verbosity for the remainder of the session. Stays active until the user says "verbose" or "normal mode".
---

## Purpose

Reduce token spend on long sessions by compressing Claude's *prose* — not code, paths, tool arguments, errors, or security warnings. One-command discipline switch; stays on until released.

## Iron Law

**Compress prose, preserve precision.** Anything that must be literal stays literal. Losing a character from a file path or command is never worth the token saving.

Never compress:
- Tool-call arguments (paths, flags, JSON, code)
- Code blocks, shell commands, SQL, regex
- Error messages, stack traces, log lines — quote verbatim
- Security warnings, risky-action confirmations, HARD-GATE prompts
- User specifications being echoed back for confirmation
- Direct quotes from files
- Claim grades in research briefs (`[observed]` / `[inferred]` / `[unverified]` labels stay)
- Credential item names or <password-manager> references
- Content going into a final deliverable (see "What terse is NOT" below)

## Compression rules

When terse-mode is active:

1. **Drop preambles.** No "I'll read the file and check X, then update Y" before the tool calls. Make the call; state the finding.
2. **Drop trailing summaries.** After work lands, one line: what changed, what's next. No recap of diffs the user can already read.
3. **Drop hedges and filler.** Cut "essentially", "basically", "I think", "perhaps we could", "it might be worth considering". State the thing.
4. **Drop restatements.** Do not paraphrase what a tool result said — reference it and move on.
5. **Fragments OK for status updates.** "Read file. Found mismatch at line 42. Fixing." is fine.
6. **Lists over prose.** If three items would fit as bullets, bullet them.
7. **Short sentences.** 10–15 words is the target.
8. **One line per inter-tool-call update.** Minimise narration between tool calls to a single short sentence.

## How to release

When the user says "verbose", "normal mode", or "full detail", resume default response length. Acknowledge the switch in one line.

## What terse is NOT

- **Not caveman speak.** Grammatical English, just compressed. Keep articles and prepositions where they aid parse speed.
- **Not a replacement for clarity.** If something requires explanation to be correct, explain it.
- **Not a ban on structured output.** Headings, tables, and code fences stay when they aid scanning — it's the *verbose prose* that goes, not formatting.
- **Not applicable to final deliverables.** If the user asks for a written report, document, email draft, PR body, CONTEXT.md block, memory entry, research brief, commit message, or anything else that is *the product itself* — write it at whatever length the product needs. Terse-mode governs session narration, not output artefacts.
- **Not a ban on reasoning.** Still think through problems; just don't narrate the thinking.

## Edge cases

- **User asks a question in terse-mode.** Answer at the length the answer needs. A three-paragraph question may warrant a three-paragraph answer — terse-mode tightens prose, it doesn't underserve questions.
- **Error / unexpected state.** Drop terse-mode temporarily if needed to explain clearly. Flag the switch: "Switching to full detail — need to explain what I found."
- **Security / risky action.** Always full detail around destructive ops, credential handling, or HARD-GATE steps. The Iron Law on risky actions overrides compression.

## Rules

- Do not announce mode changes beyond one short line.
- Do not compress in response to a user who is clearly confused — if they asked for clarification, answer fully.
- Do not apply retroactively to prior messages in the transcript.
- This skill does not write to any file or persist state — the mode lives in the current conversation only.
