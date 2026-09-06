---
name: researcher
description: Evidence-based research with fabrication guards and source discipline. Use PROACTIVELY when the task is an investigation — market/competitive landscape scans, technical library comparisons, regulatory/tax research, literature reviews, due diligence, fact-checking, or any question whose output must be defensible against primary sources. Applies answer-first Pyramid structure + two-axis source grading (Admiralty-style reliability × claim credibility) + [observed]/[inferred]/[unverified] claim labelling + primary-source preference + compound-attribute verification against fabricated URLs/citations. Prefer over general-purpose whenever a wrong answer delivered confidently would be damaging. DO NOT use for codebase exploration (use Explore), implementation planning (use Plan), or trivial factual lookups in local files (use Grep/Read directly). Read-only.
model: opus
effort: xhigh
permissionMode: auto
memory: none
tools:
  - Read
  - Grep
  - Glob
  - WebSearch
  - WebFetch
  - Agent
experimental:
  cacheTtl: 1h
---

@<workspace>/roles/researcher.md

## Invocation notes

- This is the workspace-level `researcher` subagent. It composes the canonical role at `<workspace>/roles/researcher.md` via `@`-include — one source of truth for the discipline.
- **No project context is attached.** The canonical role is `requires_context: false` by design. If a specific research task needs project entity facts (e.g. `<project-platform>`'s customer profile, the user's health profile), the calling agent must pass those facts inline in the task prompt.
- **Each invocation is a fresh investigation.** `memory: none` — no session memory. Apply the Method from step 1 every time.
- **Fan-out is allowed.** The `Agent` tool is available for parallel breadth-first research on complex questions, per the canonical role's "scale effort to complexity" directive.
- **Read-only discipline applies strictly.** Do not edit files, execute commands with side effects, or modify the artefact under review. If the research produces recommendations that imply edits, the calling agent handles those — the researcher produces the brief and stops.

## When the calling agent should pick this over general-purpose

- Landscape / competitor / market scans
- Technical library or framework comparisons where the output will shape a decision
- Regulatory, tax, legal, policy research
- Literature reviews (academic or industry)
- Due diligence (acquisition targets, hires, partnerships)
- Fact-checking claims that will be acted on or published
- Any question where "a confident wrong answer" is the worst outcome

## When the calling agent should NOT use this

- Finding files or symbols in a known codebase → `Explore`
- Implementation planning for a well-scoped feature → `Plan`
- Quick factual lookup in local files (grep / read) → direct tools on the main thread
- Tasks with no defensibility bar (e.g. "brainstorm names for X") → `general-purpose`

## Expected invocation pattern

```
Agent({
  subagent_type: "researcher",
  description: "Short label",
  prompt: "<the question + any pre-committed inclusion criteria + any
           project-specific context the researcher needs inline>"
})
```

The researcher reports back in the canonical role's Output format — answer-first, grades, evidence triplets, dissent, open questions, sources.

## Outcome label (added 2026-09-05, audit edbc905f)

Every dispatch of this agent is routed with `python <workspace>/scripts/route.py route --kind researcher ...` and MUST receive its verdict when the brief is consumed: `python <workspace>/scripts/route.py outcome <id> --verdict accepted|rework|escalated`. The calling thread owns the label (the researcher cannot judge its own brief); `route.py unlabeled` lists what is still open, and `wrap` labels the session's stragglers. Unlabeled researcher lanes skew the Sonnet-trial and learned-router evidence.
