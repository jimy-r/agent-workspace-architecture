# M5. Telemetry & cost — loud failure, priced lanes

> [Learn track](README.md) · dimension: **Telemetry & cost** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can stop one unattended task on purpose and be told about it, unprompted, somewhere you already look.

The whole point of a scheduled task is that nobody is watching it — which is exactly why nobody notices when it dies. The worked failure behind this module: a morning-brief lane in a real workspace failed on an expired credential for **34 consecutive days**, wrapper exiting cleanly the whole time, alarms firing into channels whose only readers were the dead systems themselves. Detection isn't remediation, and an alarm needs a live human reader.

The cost half is the same instinct pointed at spend. Before any structural cost fix (cheaper models, new infrastructure), instrument: split consumption by lane, token class, and model, then pull configuration levers cheapest-first, one variable at a time. In the measured case, the migration that nearly shipped would have forfeited a 95% cache-hit subsidy that no price list shows.

## The patterns

- [**Pattern 3. Make silent failure loud (the dead-man's switch)**](../PATTERNS.md#p3) — every scheduled task emits a success sentinel; a watchdog raises a finding when the sentinel is missing or stale. Self-hosted, no uptime service.
- [**Pattern 15. Price the lane before you migrate it**](../PATTERNS.md#p15) — walk the transcripts before believing any per-token price list; run each cost lever as a registered trial with a kill criterion.

Cross-reference: the always-loaded baseline and its trend alarm live in [M2](02-context-economics.md) (Pattern 9).

## Do this

Pick your one scheduled or recurring automated task (backup, digest, sync — anything unattended). Give it a sentinel: on success it writes a dated marker line to a log. Add a freshness check that runs somewhere a human actually looks — session start is the honest choice — and flags when the marker is older than the task's cadence plus slack.

After a normal run the log should end with a fresh dated marker, and the check should stay quiet. With the task disabled, expect nothing until the marker is older than the cadence plus slack. After that the flag should show up wherever you wired the check, without you asking for it.

**Done-check:** kill the task deliberately (disable it for a cycle) and confirm the staleness flag surfaces where you'd genuinely see it. An alarm you had to go looking for fails the check.

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

[`check_task_freshness.py`](../samples/scripts/security/check_task_freshness.py) is the watchdog shape; [`tier_metrics.py`](../samples/scripts/tier_metrics.py) is the lane-split spend instrument. Instrument the artefact the task produces, not the wrapper's exit code — a wrapper can exit 0 with nothing written.

`check_task_freshness.py` prints one row per tracked task with a state such as `FRESH` or `STALE`, and it exits 0 only when no task is flagged. The `tier_metrics.py` report has a `Lane split` section that prices the main thread and the subagent lane separately.

## If it didn't work

- No flag yet. Check the clock first. A task disabled for less than its cadence plus slack is still fresh, so wait the window out or shorten it for the test.
- The flag exists, but only in a log or a file you had to open. That fails the done-check. Move the freshness check to session start, or into whatever you read every day.
- The sample watchdog reports `NEVER_RAN` or `NO_SENTINEL` for a task that ran. It finds logs by file name, `<task>_YYYY-MM-DD-HHMM.log`, reads the age from that name and looks inside for the configured marker string. Check the file name and the marker against its `TRACKED` table.
- `tier_metrics.py` shows `files scanned: 0`. Its `TRANSCRIPT_ROOT` still points at the placeholder directory.

---

*Next: [M6. Provenance & delegation](06-provenance-delegation.md) · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
