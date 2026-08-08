<!--
SYNTHETIC EXAMPLE. Every card below is fabricated for illustration.
No real task content, no real paths, no real dates of consequence.
Field format matches the working schema exactly; see README.md for the field table.
Areas here are projects · ops · writing · home. Pick your own; keep them categories, not stages.
-->

# Board

> **Canonical task store.** Agent-edited via the board skill; rendered to a local view.
> Grouped by CATEGORY. `status` is active | someday | done. A move is a one-line edit.
> `blocked:` is a badge on the card, not a column: a card waiting on someone stays in its own category.
> Never hand-edit the rendered HTML. Re-render after every edit.

## Backlog — notes awaiting triage

- 2026-08-06  Something odd in the nightly log around 03:10, three retries then success. Worth a look before it becomes a real failure.
- ~~2026-08-02  The importer chokes on the new column ordering; needs a proper port not a patch~~ *(Triaged 2026-08-05 → card `csv-importer-schema-port`)*
- delegate: port the CSV importer to the new schema

<!-- A note starting `delegate:` is NOT ordinary triage. The next session routes it to the
     agent-queue intake interview; it becomes a `delegate: queued` card only after that
     interview runs. A scratch note alone never queues work. -->

### Decide: self-host the metrics page or use the hosted service
id: decide-metrics-hosting
status: active
area: projects
owner: me
next: Decide between self-hosting on the existing box and the hosted tier at $12/mo. Write the choice in the card body.
effort: S
due: 2026-08-15
blocked:
links: <workspace>/notes/metrics-options.md
source: <workspace>/tasks/To Do Notes.md:18
why: Blocks the dashboard work; both downstream tasks branch on this answer.
queue:
created: 2026-08-04
updated: 2026-08-06

Self-host: no recurring cost, one more thing to patch. Hosted: $144/yr, someone else's uptime problem.
The decision IS the next action. Do not turn this into "research metrics options".

### Port the CSV importer to the new schema
id: csv-importer-schema-port
status: active
area: projects
owner: agent
delegate: queued
next: Rewrite the column mapping in the importer against the v3 schema and extend the fixture tests.
effort: M
due:
blocked:
links: <workspace>/example-project/, <workspace>/example-project/docs/schema-v3.md
source: <workspace>/tasks/To Do Notes.md:22
why: The v2 mapping breaks on reordered columns; every import since the schema change is silently dropping two fields.
queue:
created: 2026-08-05
updated: 2026-08-07

done-when: pytest green including new fixture cases for reordered and missing columns; no network calls in tests; branch left uncommitted.
write-scope: <workspace>/example-project/ only.
constraints: Extend the existing fixture-based test file rather than adding a new harness. Do not touch the deployed config.
ruling: If the v3 schema turns out to allow optional columns, treat a missing optional column as a warning, not a hard failure.

### Rotate the object-storage credential used by the backup job
id: rotate-backup-credential
status: active
area: ops
owner: me
next: Generate a new key in the storage console, then update the backup profile and run one verify pass.
effort: S
due: 2026-08-20
blocked:
links: <workspace>/scripts/backup-restic.ps1
source: <workspace>/tasks/To Do Notes.md:41
why: The current key predates the credential-discipline rule and has no rotation date on it.
queue:
created: 2026-08-01
updated: 2026-08-01

### Audit findings awaiting a decision
id: audit-findings-backlog
status: active
area: ops
owner: me
next: Run the audit-workthrough skill and drain the pending findings, oldest first.
effort: M
due:
blocked:
links: <workspace>/tasks/audit/SETUP_REVIEW.md
source:
why: Roll-up card. The ledger stays canonical; this card exists so the count is visible without exploding into one card per finding.
queue: audit
created: 2026-07-28
updated: 2026-08-06

### Chase the supplier on the replacement power supply
id: nas-psu-replacement
status: active
area: home
owner: external
next: Wait on the supplier's RMA number, then book the courier pickup.
effort: S
due:
blocked: Supplier RMA requested 2026-07-29, no reference number yet
links:
source: <workspace>/tasks/To Do Notes.md:57
why: The spare unit is running on the old supply; a second failure takes the array offline.
queue:
created: 2026-07-29
updated: 2026-08-06

### Cut the long-form draft down to eight sections
id: draft-section-trim
status: active
area: writing
owner: me
priority: high
next: Open the draft and mark every section that survives the cut, then delete the rest in one pass.
effort: M
due: 2026-08-12
blocked:
links: <workspace>/notes/long-form-draft.md
source: <workspace>/tasks/To Do Notes.md:11
why: Fourteen sections is two articles pretending to be one. The cut is the thing standing between the draft and a publish date.
queue:
created: 2026-08-03
updated: 2026-08-07

### Label the electrical panel properly
id: label-electrical-panel
status: active
area: home
owner: me
next: Buy a label roll, then map each breaker by switching it off and walking the house.
effort: S
due:
blocked:
links:
source: <workspace>/tasks/To Do Notes.md:63
why: Two unlabelled breakers turned a five-minute job into an hour last time.
queue:
created: 2026-07-25
updated: 2026-07-25

### Verify the backup restore round-trip
id: backup-restore-verify
status: active
area: ops
owner: me
next: Run the verify script, then restore one file to a scratch folder and diff it against the original.
effort: S
due: 2026-09-30
repeat: quarterly
last_done: 2026-06-30
blocked:
links: <workspace>/scripts/restic-verify.ps1
source:
why: A backup that has never been restored is a hypothesis, not a backup.
queue:
created: 2026-04-02
updated: 2026-06-30

<!-- RECURRING CARD. Lives in the collapsed Recurring lane, excluded from column counts.
     NEVER set status: done on this. Ticking it rolls `due` forward a quarter and stamps
     `last_done`. To retire the rhythm, delete the `repeat:` field. -->

### Read up on the new query planner internals
id: query-planner-deep-dive
status: someday
area: projects
owner: me
next: Pick one of the three design docs and read it end to end.
effort: L
due:
blocked:
links:
source: <workspace>/tasks/To Do Notes.md:9
why: Interesting, not urgent. Parked deliberately so it stops competing with dated work.
queue:
created: 2026-06-18
updated: 2026-07-14

### Write up the caching experiment results
id: caching-experiment-writeup
status: done
area: writing
owner: me
next: Publish the results table and the one paragraph on why the naive version won.
effort: S
due:
blocked:
links: <workspace>/notes/caching-experiment.md
source: <workspace>/tasks/To Do Notes.md:14
why: The numbers were surprising enough to be worth a short write-up while they were fresh.
queue:
created: 2026-07-30
updated: 2026-08-06

result: 2026-08-06 — published; the source note was struck through in the history file on close.
