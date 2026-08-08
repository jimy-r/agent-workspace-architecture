# WORKFLOW.md: how this workspace actually runs

> **Scope:** what a day of using the workspace looks like. Not what's in it; the structural map lives in [META_ARCHITECTURE.md](META_ARCHITECTURE.md).

The other docs describe the pieces. This file describes how they're held together in practice: session discipline, entry-point choices, how a task moves from thought to done. It's one person's habits, not a prescription.

---

## Core mental model

**Sessions are task-scoped.** One session ≈ one task. The session title matches a bullet on the task list. When the task is done, the session is closed out and archived.

**Many sessions run in parallel.** Two or three live at once, nine or ten total in various states: some actively worked on, some paused mid-task, some waiting on a subagent. Max observed: five live, ten total.

**The workspace root is the launchpad.** Every session starts at `<workspace>/` (the top of the personal Claude directory). Projects branch off from there. Sessions don't `cd` into project folders; CLAUDE.md auto-load and MCP scopes handle the rest.

**Delegation is trusted, not micromanaged.** Role bindings (`@<project>-<role>`) and subagents aren't invoked by hand. The main thread picks the right subagent and role based on CSO-style descriptions, pulls project `CONTEXT.md` as needed, and routes itself.

---

## The command-dashboard model

Work happens primarily in the **Claude desktop app**, treated as a command dashboard. Each live session is a pane. The CLI terminal still exists but has faded; the desktop app's session-juggling UI is what makes the parallelism workable.

**Remote terminals.** One to three Remote Control terminal sessions are started in the morning and left running. They're not manually attended; they're there so the phone can dispatch commands into them from elsewhere.

**Phone.** The Claude Android app speaks to those remote terminals. Combined with voice dictation, this lets work continue away from the desk: meeting breaks, evenings, walking, bed.

**Voice.** OS-level Whisper dictation (a commercial hotkey-to-text tool) replaced an earlier home-built voice channel MCP. Works identically across desktop and phone.

**Surfaces retained but unused day-to-day.** A web voice UI and a Discord dispatch channel exist in the architecture but aren't in the current flow. Kept as capability, not as daily tooling.

---

## A day in the workspace

### Morning
- Read the morning brief email: appointments, weather, AI news, current task-list state, open questions, overnight activity.
- Start one to three Remote Control terminals (for later phone dispatch).
- Open the Claude desktop app. Resume an in-progress session or open a fresh one.
- On fresh sessions: run the [`orient`](samples/.claude/skills/orient/SKILL.md) skill first, then the [`tasks`](samples/.claude/skills/tasks/SKILL.md) skill. That's the boot sequence.

### During the day
- Work flows across two or three live sessions. When one hits a blocker or waits on a subagent, focus shifts to another. Sessions aren't "background"; they're parked and resumed.
- New task surfaces → new session, named for the task. Context doesn't get switched inside an existing session; a new session gets spun up.
- Items that don't warrant action this minute → dumped into the board's scratchpad, unstructured. A later session turns each note into a card carrying a literal next action and an honest owner, and strikes the note it came from.

### Away from desk
- Phone takes over. Claude Android app + voice dictation + Remote Control terminals. Same workflow, different surface.
- Can run several hours a day this way; the remote terminals keep state warm between interactions.

### Close-out
- Task complete → invoke the [`wrap`](samples/.claude/skills/wrap/SKILL.md) skill. It handles the close-out ritual: close the card, resolve anything linked to it, sweep registries, and log a per-task token record for the metrics page.
- Task ongoing → just walk away. Session stays open. Pick up next time.

---

## Lifecycle of a single session

1. **Open.** Launch from the desktop app (or the CLI launcher script).
2. **Name.** The session title matches a task from the task list.
3. **Orient.** `orient` skill for fresh sessions; `tasks` skill to see what's open.
4. **Plan (sometimes).** If the change is non-trivial, the session writes a plan to a todo file before implementing. Threshold is fluid; simple changes skip planning.
5. **Work.** The main thread does the bulk; subagents spawn for research, exploration, parallel analysis.
6. **Wrap or park.** `wrap` skill if done; walk away if continuing tomorrow.
7. **Archive.** Finished sessions are archived rather than deleted.

---

## How tasks flow

### Capture first, action later
- Raw notes land in the board's scratchpad. No pressure to structure them at capture time, and a note is never counted as a task until someone decides it is one.
- Triage happens in a session. Each note becomes a card with a real next action and an honest owner, or it gets struck as nothing. Judgment sits here, not at capture.
- The user works cards as interest dictates, not strict priority or FIFO. The board is a standing offer, not a schedule.

### When the user plans, when the agent plans
- Session starts → user states the goal → agent proposes a plan → user OKs or redirects.
- No fixed threshold for "needs a plan first". Simple changes just happen. Anything structural gets a plan written before code.

### Delegation, and the colleague that used to do it
- A heartbeat agent held this job until August 2026. Every two hours it read the task list, held items until they looked actionable, batched similar questions, and asked for whatever context it judged missing. It did not grind the queue mechanically, and that part worked.
- The asking is what broke. Questions went into a separate tracker file and thirteen accumulated unanswered, each one freezing the task behind it. Separately, the schedule itself failed dark for about five weeks behind an expired credential nobody was watching.
- Delegation is now explicit. The user marks a card delegated, answers a short intake round on the spot (what done looks like, which folders are writable, what constrains the approach, how the likely forks should be ruled), and a drain skill works the queued cards on demand inside a live session.
- A question raised mid-work goes onto the card being worked, in the same view the user already reads. Answering it is a one-line edit.

The interplay between queued delegation and in-session planning is still under active tuning. Two cards have been drained this way, both clean, which is early evidence rather than a track record.

---

## Delegation: trust the routing

- **Don't invoke `@<project>-<role>` manually.** The CSO-style descriptions on role bindings let the main thread pick the right one automatically. Project `CONTEXT.md` files ride along when relevant.
- **Don't manually fan out to `researcher` / `Explore` / `general-purpose`.** The main thread judges when parallel research pays. Over-directing wastes context.
- **Trust compaction + memory.** Long sessions compact as they go; the memory system carries durable facts across sessions.

The pattern: hand the main thread the task and the context pointers; let it route the rest.

---

## What the workspace gives you that a single long loop does not

- **Resumable state across many surfaces.** Desktop, phone, voice, and remote terminals all see the same card store and memory.
- **A morning brief that is actually actionable.** Calendar, weather, AI news, open questions, and overnight activity in one place.
- **A delegation queue where a question tracker used to sit.** The old claim here was that a background agent narrowing its questions kept work from stalling on vague input. Work stalled anyway, thirteen questions deep, in a file nobody opened. Intent is now taken at the moment of delegation from the person who holds it, and anything the work raises later is written on the card being worked.
- **Typed memory.** User profile, feedback, project state, and reference pointers stay separable rather than collapsing into one long note.
- **A credentials discipline.** Every API key and token lives in a password manager; files reference item names only, never values.
- **Routine skills.** `orient`, `tasks`, `wrap`, `verify-completion`, and `systematic-debugging`, invokable the same way whether you're at desktop, phone, or voice.

The cost is real: when the platform ships a new feature, integrating it is work, and the structure can lag what a single autonomous loop gives you out of the box.

---

## The open tension

Worth naming: there's a real question about how much structure versus autonomy is optimal.

**Structured workspaces** (this approach) buy: predictable entry points, reusable skills and roles, a shared card store, credential safety, a morning brief, an explicit delegation queue. Cost: platform features land in the framework on a lag; integrations are ongoing work.

**Autonomous agents** (single loop, long-horizon) buy: pace-of-platform, less integration work, more emergent behaviour. Cost: weaker auditability, fewer guardrails, harder to split work across days and surfaces.

One direction being explored is a **hybrid**: a human at the top, a workspace of *executive* agents (structured, reviewable), and more independent autonomous agents below. The executive agents review and prune candidate solutions from the autonomous ones, evolutionary rather than prescriptive. Still a direction of travel, not a delivered design.

If that shape resonates, you're the audience for this repo. If it feels over-structured, you'll probably settle closer to a single Claude loop plus a memory file.

---

*Last verified against the repo structure on **2026-08-08**.*
