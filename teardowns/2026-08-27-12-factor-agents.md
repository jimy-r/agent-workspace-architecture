# Teardown: 12-Factor Agents

- **Subject:** https://github.com/humanlayer/12-factor-agents
- **Revision read:** `d20c728` (last substantive push 2025-09-21; 25.5k stars at reading)
- **Patterns present:** 1, 2, 9, 12, 17 (several partially — see body)
- **Patterns absent worth noting:** 3, 5, 6, 7, 8, 11, 16
- **Date:** 2026-08-27

## What it is

Dex Horthy's principles for building production LLM applications, written in the spirit of the original twelve-factor apps: twelve short essays arguing that reliable agents are mostly deterministic software with LLM steps placed deliberately, not prompt-and-tool-bag loops. It became one of the most-cited methodology documents of the 2025 agent wave, and its "context engineering" framing (factor 3) entered the vocabulary before the term went mainstream.

## What works

**The altitude of the core claim.** The opening argument (`README.md`) is that most things billing themselves as agents are deterministic code with LLM calls at the points where they buy the most, and that this is a feature. A year of harness-era experience has borne this out almost completely. Our own workspace runs on the same conviction: deterministic discovery with human judgment at the gate, code for retrieval and filtering, the model only where judgment lives.

**Structured human contact (factor 7).** `factor-07-contact-humans-with-tools.md` makes contacting a human a first-class structured intent (`request_human_input` with urgency and format fields) rather than a plaintext fallback. This is still ahead of most shipped harnesses, which treat the human channel as chat. It is the application-side precondition for what our Pattern 2 (classify-then-act) and Pattern 14 (a delegation queue with pre-ruled forks) do at the workspace layer: a human contact that carries structure can be routed, queued, and answered asynchronously.

**The stateless reducer (factor 12) and unified state (factor 5).** Modelling the agent as a fold over an event list, with execution state inferred from business state rather than tracked beside it, is what makes launch/pause/resume (factor 6) cheap. Factor 5's honesty is worth crediting: it argues for unification *where possible* and names the cases where it is not, instead of universalising.

**Small, focused agents (factor 10).** The reasoning is context-window management rather than anthropomorphic role-play, and the 3–20 step bound is stated with its rationale. This is Pattern 1's composition argument arrived at from the reliability direction, and factor 10's "do we still need this if models get smarter" section answers its own future correctly.

## The trade-offs

**Own everything, pay for everything.** Factors 2, 3, and 8 (own your prompts, context window, control flow) trade framework convenience for control, and the guide is candid that this is a bet on flexibility. The cost shows up as bespoke plumbing every adopter rebuilds: the guide teaches the shape but ships no reusable substrate, which is a deliberate scope choice and a real adoption tax.

**Application altitude.** The twelve factors describe building *one agent application* well. Operating a fleet of them day after day (the workspace altitude) is out of frame. That is not a defect of the guide; it marks where its coverage ends, and most of what is absent below sits past that boundary.

**Quiet since late 2025.** At the revision read, the repo's last substantive push was 2025-09-21. The factors have aged well, but the harness-era conventions that emerged after (skills as routable instruction files, hook-based guards, workspace-level configuration ecosystems) are absent from a document that would today engage with them.

## What's conspicuously absent

Measured against the patterns this repository documents, the gaps cluster in exactly one place: everything that keeps an agent system honest *over time*.

- **Silent failure (Pattern 3).** Factor 11 triggers agents from anywhere, including schedules, but nothing addresses the scheduled agent that stops firing. Our measured experience: a credential expired without error and a lane failed dark for five weeks. A methodology that includes cron-shaped triggering needs a dead-man's switch beside it.
- **Memory write discipline and provenance (Patterns 5 and 16).** Factor 3 names memory as context input, but nothing governs the write side: what enters durable memory, how a claim carries its source, how a verified fact stays distinguishable from a plausible guess. This is the largest gap for anyone running the factors over months rather than sessions.
- **Credentials (Pattern 6) and deterministic guards (Pattern 7).** The factors trust good structure to produce good behaviour. Production experience says structure needs a blocklist under it: a ten-line PreToolUse check catches the accidental damage that no amount of owned control flow prevents.
- **Measurement (Patterns 8 and 11).** There is no evaluation harness discipline, no notion that each principle is a hypothesis an adopter should verify against their own system. The factors are asserted from experience (credibly), never framed as measurable.

## What this teaches

The two pattern sets compose rather than compete. 12-Factor Agents is the strongest available statement of the *application layer*: how one agent's runtime should be shaped. The patterns here describe the *operational layer* around it: verification, provenance, guards, and measurement for agents that run unattended and accumulate state. Several factors are preconditions for our patterns (structured human contact enables delegation queues; owned context windows enable context budgeting), and none contradict them. An adopter building on the factors should treat the absences above as the checklist of what their second month of operation will demand.
