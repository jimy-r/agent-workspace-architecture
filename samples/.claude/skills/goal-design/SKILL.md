---
name: goal-design
description: Pre-flight interview that turns a fuzzy intent into a best-practice /goal loop artifact - folds in project context and gates on a checkable stop-condition before writing the goal prompt you feed into /goal. Invoke via "goal design", "/goal-design", "design a goal loop", "build a goal prompt".
---

> Redacted sample. Generic placeholders (`<workspace>`, generic example commands) stand in for one operator's specifics.

Base directory for this skill: `<workspace>/.claude/skills/goal-design`

## Purpose

`/goal <condition>` runs the agent autonomously across turns until a fast model judges the condition met. Its single point of failure is the **condition**: a vague one loops forever or stops on a false positive; a sharp, checkable one is reliable. This skill is the pre-flight you run BEFORE `/goal` — it interviews you, folds in the project's own context, and writes a ready-to-paste goal artifact whose stop-condition is genuinely verifiable. You then feed that artifact into `/goal` as a deliberate, separate step.

## How `/goal` actually works (design to these facts)

Verified against the Claude Code docs:

- `/goal <condition text>` (≤4,000 chars) sets a completion condition; the agent keeps taking turns until satisfied. No separate prompt needed — setting it starts a turn.
- **A separate fast model judges the condition each turn, reading ONLY the conversation transcript.** It does NOT run commands or read files itself. So the condition is only "checkable" if **the agent's own output surfaces the proof in the transcript** — e.g. the agent runs the test suite, the result lands in the transcript, the evaluator reads it.
- **No default cap.** You MUST include a bound clause (`... or stop after N turns` / `... or stop after 1 hour`), especially when running unattended (no per-turn prompt to interrupt it).
- Headless: `claude -p "/goal ..."`. A goal active at session end resumes on `--continue` / `--resume` (turn count + timer reset).
- Requires hooks enabled; complements auto mode (auto removes per-tool prompts, `/goal` removes per-turn prompts).
- Clear with `/goal clear` (or `off`/`stop`/`reset`).

## Context durability — compaction, /clear, and long goals

The `/goal` × context-pressure interaction is **largely undocumented**, so design every goal to survive it rather than trust the harness. Confirmed facts:

- **`/clear` CANCELS an active goal** — never `/clear` mid-loop. `/compact` continues the same session (use it if you must intervene); auto-compaction fires automatically as the window fills.
- **The evaluator can lose the proof.** It reads only the transcript; a compaction may summarize away the evidence (test output, a count) — which can stop the loop on a false "looks done" OR hide real completion. Nothing preserves the condition's *evidence* across compaction.
- **Resume resets the bound.** A goal active at session end carries its *condition* over on `--continue`/`--resume`, but the turn count + timer + token baseline RESET — so a "stop after N turns" bound starts fresh.

The four rules that neutralize this — bake them into every artifact:
1. **Self-prove every turn.** The condition must make the agent RE-RUN the check and surface its output each turn, so compaction cannot matter — the next turn regenerates fresh proof into the transcript. The single most important rule.
2. **Checkpoint to a file, not the transcript.** For any goal that may exceed one window, write progress to a durable file and READ IT FIRST each turn, so state recovers from disk after a compaction, not from a lossy summary.
3. **Require a concrete signal, never "the task is complete."** A vague condition is exactly what a summary can spuriously satisfy; `exits 0` / `count == 0` / `file contains X`, re-checked each turn, cannot.
4. **Fit one window, or decompose.** If it clearly will not finish in one context window, split into sub-goals (separate `/goal` runs) or make it file-checkpointed and resumable — do not write a 200-turn goal and hope.

## Iron Law — the checkable-condition gate

**Do not produce a `/goal` artifact unless the stop-condition is something the agent's output will surface in the transcript and a fast-model reader can judge true/false.** Checkable: "all tests in `tests/auth` pass (`pytest -q tests/auth` exits 0)", "`ruff check .` is clean", "the project self-test prints PASS", "the lint/type gate shows 0 errors", "the file `X` contains a row for every Y". NOT checkable: "improve the code", "make it better", "design the architecture", "research the options well". If the intent has no transcript-surfaceable check, STOP and route to the right tool instead (a one-pass reasoning skill for design, a research flow for investigation, a normal session for judgement work) — say plainly that `/goal` is the wrong instrument and why. Never paper over a vague goal with a checkable-sounding but unmeasurable clause.

## Procedure

### 1. Scope + load context
Determine which project/area the goal targets (infer from the working directory + conversation; confirm in one line). Then READ that project's grounding so the goal is concrete, not generic: its `CLAUDE.md` / `CONTEXT.md`, the real test / lint / build commands, and any plan or done-criteria already written. Surface what you found so the interview is anchored in reality.

### 2. Interview — fill the blanks, one topic at a time
Ask only what context did not already answer. Drive toward:
1. **Outcome** — what "done" looks like in one or two sentences.
2. **Verifiable stop-condition** — the measurable end state. Push hard; if the user gives a vague one, propose 2-3 checkable reframings drawn from the project's real commands. This is where most of the value is.
3. **The exact check** — the command the agent runs to prove it + the expected signal (`exits 0`, prints `PASS`, `count == 0`, clean tree). The artifact must instruct the agent to RUN this each turn so the transcript carries the proof.
4. **Bound** — turns or time (`or stop after N turns`). Mandatory.
5. **Scope / guardrails** — what must NOT change en route. These become the constraints clause.
6. **Context to read first** — the files the loop should open before acting, so it doesn't rediscover them every turn.
7. **Window-fit + durability** — will this plausibly exceed one context window? If yes (or unsure), define a durable progress file the loop writes after each step and reads first each turn, and consider splitting into sub-goals. Confirm the condition re-runs the check every turn (durability rule 1).

### 3. Gate
Apply the Iron Law. If no checkable condition survives the interview, do not write an artifact — explain and route away. Otherwise continue.

### 4. Write the artifact
Write `tasks/goals/<slug>.md` using the template below. Keep the `/goal` condition line itself ≤4,000 chars and self-contained — once pasted it IS the directive.

### 5. Stop (do not launch)
Print the artifact path and the ready `/goal` command. Do NOT run `/goal` — launching the autonomous loop stays a deliberate user action.

## Artifact template

```markdown
# Goal: <title>   (designed <YYYY-MM-DD>)

## Outcome
<one or two lines: what done looks like>

## /goal command  (paste to launch)
/goal <measurable end state>, proven by re-running <exact check> each turn until it shows <expected signal>; log progress to <progress file>; constraints: <what must not change>; or stop after <N> turns.

## Verification (how the loop proves it each turn)
- Run: `<command>`  ->  expect <exit 0 | "PASS" | count 0 | clean>
- The fast-model evaluator reads only the transcript, so the agent must RUN this check and surface its output every turn.

## Scope / guardrails
- In scope: <paths/areas>
- Do NOT change: <paths/areas/behaviours>

## Context (read first)
- <project CONTEXT.md / key files / done-criteria pointers>

## Durability (survive compaction)
- Re-run the check + surface its output EVERY turn, so a compaction cannot summarize away the proof.
- Progress file: <tasks/goals/<slug>.progress.md, or N/A if it fits one window> — write after each step, read first each turn.
- Do NOT /clear mid-goal (cancels it). Use /compact to intervene. The bound resets on --continue/--resume.

## Run notes
- Interactive: paste the /goal line above.
- Headless: claude -p "/goal <...>"   (resume an interrupted goal with --continue)
- Bound is mandatory when running unattended - never launch without the stop-after clause.
```

## Out of scope
- **Launching the loop** — this skill designs and writes; you run `/goal` yourself.
- **Goals with no checkable condition** — routed away per the Iron Law, never forced into a `/goal`.
- **Editing `/goal` itself or settings** — it only produces an artifact.

## Notes
- Companion to the autonomy controls (plan mode / `/goal` / task tools) and to a one-pass reasoning skill (the right tool when the work is judgement, not a checkable loop).
- One artifact per goal; they accumulate in `tasks/goals/` as a re-runnable record.
