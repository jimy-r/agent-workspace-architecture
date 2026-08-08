# Task board — module design

One canonical markdown card store for everything outstanding, rendered to a local web view, with an **explicit delegation queue** for the work an agent may action.

This module is the successor to the scheduled project-manager agent in [`../tasks/HEARTBEAT.md`](../tasks/HEARTBEAT.md), retired in the source workspace in August 2026. The succession rationale is at the bottom of this file; read it if you are choosing between a discovery-driven background agent and an operator-driven queue.

## Files here

| File | What it is |
|---|---|
| [`README.md`](README.md) | This design doc. |
| [`board.example.md`](board.example.md) | A synthetic card store: ten cards across four areas, plus a backlog note section. Field format matches the real schema exactly. |
| [`agent-queue.SKILL.example.md`](agent-queue.SKILL.example.md) | The delegation skill: intake interview, drain procedure, Iron Laws. Redacted from the working version. |

## The problem

Task state had scattered across six stores: a prose notes file that had grown past 130 KB, a question tracker, an implementation-plan file, an audit finding ledger, a review queue, and a lesson-candidate queue. There was no single view. Worse, every item carried a paragraph of history you had to re-read before you could tell what to *do* next. Capture drifted back to the phone notepad, and work got picked up ad hoc.

The fix has two properties. One card per outstanding thing, carrying a literal next action and an honest owner. And one file that is the truth, so every other surface is a render of it.

## The card schema

A flat list of `###` cards in one markdown file. No nesting, no per-column sections, no YAML.

```text
### Rotate the object-storage credential used by the backup job
id: rotate-backup-credential
status: active
area: ops
owner: me
next: Generate a new key in the storage console, then update the backup profile.
effort: S
due: 2026-08-20
blocked:
links: <workspace>/scripts/backup-restic.ps1
source: <workspace>/tasks/To Do Notes.md:41
why: The current key predates the credential-discipline rule and has no rotation date.
queue:
created: 2026-08-04
updated: 2026-08-04

Optional free-text body, running until the next ###.
```

| Field | Meaning |
|---|---|
| `id` | Stable kebab-case identifier. The one thing an edit matches on. |
| `status` | `active` (on the board) · `someday` (parked, collapsed at the foot of its column) · `done` (the view keeps the last 14 days). |
| `area` | **The column.** A category, not a stage. Four in the example set: `projects` · `ops` · `writing` · `home`. |
| `owner` | `me` (only the operator can) · `agent` (a session could do it cold from the links) · `external` (waiting on someone else). |
| `next` | The literal next physical action. Load-bearing; see rule 3. |
| `effort` | `S` · `M` · `L`. Also the execution budget when the card is delegated. |
| `due` | `YYYY-MM-DD`. On a recurring card this means the next occurrence. |
| `blocked` | Free text naming what or who the card waits on. A badge, never a status. |
| `links` | Paths or URLs carrying the context. Cards point at history; they never copy it. |
| `source` | Where the card came from, as `path:line`. Used to strike the originating note on close. |
| `why` | One line of justification, so a stale card can be judged without opening its links. |
| `queue` | Only on rolled-up machine-backlog cards (`audit` · `questions` · `lessons` · `reviews`); the count is injected at render. |
| `created` / `updated` | Dates. `created` is load-bearing: a card newer than three days floats to the top of its column, which is what makes a freshly triaged note visible. |
| `priority` | Optional `high` · `med` · `low`. Set it only where importance genuinely differs from the deadline. |
| `repeat` | Optional. Makes the card a standing rhythm; see the recurring lane below. |
| `last_done` | Optional. Stamped when a rhythm is ticked. |
| `delegate` | Optional `queued`. The operator's standing authorization for the drain; see the agent queue below. |

Because `status` and `area` are fields, moving a card is a one-line edit. Nothing has to be cut and pasted between sections, which is the failure mode that makes hand-maintained kanban files rot.

## Three rules carry the module

### 1. Columns are categories, never workflow stages

A `next` / `doing` / `waiting` layout was built first and rejected inside a day. Workflow lanes force a second bookkeeping question on every card ("which stage is this in now?") that has nothing to do with getting the work done, and they scatter one area's cards across three columns so you can never see a domain whole.

Waiting is the `blocked:` field. It renders as a badge and keeps the card in its own category, where you go looking for it. A saved filter finds every blocked card when you want that view.

Two exceptions exist, the recurring lane and the agent queue. Both are kinds of card rather than stages. Both hold cards that behave differently from ordinary tasks, not cards at a different point in a pipeline.

### 2. `owner:` is the highest-value field

`me` means only the operator can do it: a decision, a login, a signature, a call, a payment. `agent` means a session could do it cold from the links. `external` means someone else holds it.

The board's whole job is to answer "what is actually on me" in one glance. Every other field supports that question. An honest `owner` field also stops the quiet inflation where everything looks like the operator's problem, which is the state that makes a task list feel heavier than the work it describes.

### 3. A card without a literal next action is not a card

`next:` must be a physical step. "Open the storage console and generate a new key" is a next action. "Sort out credential rotation" is a topic, and a topic on a board is a small tax you pay every time you read the column.

When the real next step is a decision, write the decision as the action: "Decide: self-host the metrics page or use the hosted one." When nobody knows the next step, the next step is finding out. The one thing never permitted is an invented plausible-sounding step, which is why quick-adds land with the honest placeholder `Define the next action.` and a weekly review lens surfaces them.

## The recurring lane

A card carrying `repeat:` (`daily` · `weekly` · `fortnightly` · `monthly` · `quarterly` · `yearly` · `<N>d`) is a **rhythm, not a task**. It leaves its category column and renders in a collapsed lane, excluded from every column and status count so standing commitments never inflate the "outstanding work" figure.

Iron rule: **never close a recurring card.** Setting `status: done` on a rhythm retires a commitment that is supposed to come back. Ticking it rolls `due` forward one cycle and stamps `last_done`. To stop a rhythm you delete its `repeat:` field, which turns it back into an ordinary card you can close.

## The agent queue — delegation is explicit

`delegate: queued` on a card is the operator's standing authorization for a drain session to action it. That field is the entire authorization surface. Everything else on the board is out of scope for the agent, however obvious it looks.

Four properties make this work:

- **Only the operator's direct instruction sets the field.** The triage pass never sets it, and no agent invents queue entries. Away from a session, the operator types a scratchpad note starting `delegate:`; the next session routes it to the intake interview rather than ordinary triage.
- **An intake interview fills context at delegation time**, which is when the operator has the context in their head. The interview drafts every field it can from the conversation first, then asks one short round: what does done look like (always confirmed, never inferred), which folders may be written to, what constraints apply, and what predictable forks should be pre-ruled. Answers land as `done-when:`, `write-scope:`, `constraints:` and `ruling:` body lines that the drain honours.
- **A template floor gates actionability.** A queued card needs a literal `next:`, a `links:` pointer to an existing folder or doc, a `done-when:` body line, and an `effort:`. A card missing any of them gets a `blocked:` note naming the gap, never a guess.
- **The board is the only question surface.** A drain that hits a genuine fork writes the question into the card's `blocked:` field and moves on. The operator answers by clearing `blocked:`, and the next drain picks it up. Questions live on the thing they are about, so answering one is a single edit in the same view the operator already reads.

Queued cards render in a dedicated section above the recurring lane, wearing a badge. Unlike rhythms they still count in every status, owner and area figure, and on `status: done` they leave the queue for the Done section like any other card.

Full procedure: [`agent-queue.SKILL.example.md`](agent-queue.SKILL.example.md).

## Capture is thoughtless; triage is where judgment happens

Two motions, both writing to disk immediately:

1. **Quick-add a card.** The `+` on a column header, for a thing that is already a task with an obvious home.
2. **Dump a note.** A working-notes scratchpad above the board autosaves to a plain markdown file, for a thought that isn't a clean card yet.

Then, in a session, an agent reads the scratchpad, turns each note into a card with a real next action and an honest owner, and strikes the lifted notes. Notes are never counted as cards and never inflate the "needs you" figure, so dumping into the pad costs nothing. A note is not a task until someone decides it is.

Notes are struck through, never deleted. The strike is the audit trail, and it stops the same note being triaged twice.

## Markdown is the truth; HTML is a view

The card store is markdown because agents re-ingest it. The rendered page is a view, overwritten on every render, and nobody hand-edits it. This follows the workspace-wide rule: anything a model reads back stays markdown, and HTML is generated from it.

The renderer validates before it writes, and **a malformed card is a hard error that blocks the render**. A card silently vanishing is the one failure that would destroy trust in the board, so the failure mode is a loud refusal rather than a partial render.

## The served page

A local server re-renders from the markdown on every request and writes edits straight back to it. Ticking a card done, quick-adding, and saving a scratch note all edit the file on disk immediately. There is no browser buffer holding canonical state and nothing to sync. Only view preferences (drag order, density, focus filter, snooze) stay in browser storage, and an agent reading the board should treat the file's order as canonical because the operator's drag order is invisible to it.

Writes are guarded:

- **Per-record block edits only.** Split the file into `###` blocks, match by `id`, rewrite that block. Never a file-spanning regex.
- **Atomic replace**, with a rollback if the result would not parse or would touch a second card.
- **Refuse to edit an already-broken file.**
- **Refuse if the file changed on disk mid-edit.** Other sessions write this file too. A concurrent write is a visible error, never a silent clobber.
- **Loopback by default.** A token is mandatory for any non-loopback bind, and the `Host` header is allowlisted on every route so a random web page cannot reach a local board over DNS rebinding.

## Decay is shown, not hidden

Cards untouched for more than three weeks are flagged in the view, as are long-blocked cards. A weekly review lens collects everything stale or carrying the placeholder next action.

A board that rots quietly is worse than no board, because it keeps the reassurance of a system while losing the coverage. Making the rot visible is cheaper than preventing it.

## Machine queues roll up to one card each

The audit finding ledger, the open questions, the lesson candidates, and the review queue stay canonical in their own systems and appear here as one card each, carrying a live count. They are never exploded into individual cards. Fifty audit findings as fifty cards recreates exactly the overwhelm the board exists to remove, in prettier form.

## Metrics ride the close-out ritual

A `/metrics` page charts per-task cost and weekly throughput. The data behind it is written by the close-out ritual, where a `wrap` step logs a per-task token record as work finishes.

That makes freshness **event-driven, never scheduled**, and the page says so on its face. A stale tail means no close-out has run, not that capacity dropped. A scheduled refresh would have been the obvious build, and it would have reintroduced the exact fragility described below.

## Why this replaced the scheduled agent

The predecessor ran every two hours on a classify-then-act cycle: read the task files, sort each item into `has-default` / `needs-intent` / `out-of-scope`, build the confident ones in a sandbox, and post clarifying questions for the rest. The design is documented in [`../tasks/HEARTBEAT.md`](../tasks/HEARTBEAT.md) and as Pattern 2 in [`../../PATTERNS.md`](../../PATTERNS.md). It was paused mid-2026 and retired outright. Two failure classes killed it.

**Intent inference.** The classify-then-act flow put questions into a separate tracker file and waited. Thirteen question blocks accumulated unanswered. Work stalled on a channel nobody read, and the agent kept generating more of it, because generating a question was cheap and answering one required opening a file that was never in anyone's path. The board inverts this: questions attach to the card they are about, in the view the operator already looks at, and answering is a one-line edit.

**Unattended-runtime fragility.** The scheduled runs rode an ambient credential that expired silently. Roughly five weeks of runs failed dark. The dead-man's-switch alarms fired correctly and landed in a channel whose only readers were the other scheduled systems, which were dead for the same reason. Detection is not remediation when the alarm path shares a failure mode with the thing it watches.

The successor keeps the good half of the old design (a queue, a review gate, sandboxed work, a rejection memory) and drops the two parts that failed. The agent no longer discovers work; a card in the queue **is** the authorization. And there is deliberately no cron: drains run in an interactive session, on demand, with the session-start briefing surfacing the queue count so the queue cannot go unnoticed the way the question tracker did.

The first drain completed 2 of 2 cards without rework. That is one data point, which is why the module is registered with a review date and a kill condition: an unused queue, or output that needs reworking more often than not, cuts it. A schedule gets reconsidered only after manual drains prove the outputs land clean, and only once the headless-credential and freshness-sentinel gaps have real answers.

## Adopting a thinner version

The whole module is not the entry point. In order of value:

1. One markdown file, `###` cards, `status` and `area` as fields. Read it directly; skip the renderer entirely.
2. Add `owner:` and enforce rule 3 on `next:`. This is where most of the benefit lives.
3. Add the render step once reading the raw file gets tiring.
4. Add `delegate: queued` and the intake interview only when you actually have work you want an agent to do unattended.

Steps 1 and 2 need no code.

---

*Last verified against the repo structure on **2026-08-08**.*
