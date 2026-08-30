# M5. Telemetry & cost — loud failure, priced lanes

> [Learn track](README.md) · dimension: **Telemetry & cost** in the [maturity check](https://jamesross.ai/tools/maturity-check.html?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

The whole point of a scheduled task is that nobody is watching it — which is exactly why nobody notices when it dies. The worked failure behind this module: a morning-brief lane in a real workspace failed on an expired credential for **34 consecutive days**, wrapper exiting cleanly the whole time, alarms firing into channels whose only readers were the dead systems themselves. Detection isn't remediation, and an alarm needs a live human reader.

The cost half is the same instinct pointed at spend. Before any structural cost fix (cheaper models, new infrastructure), instrument: split consumption by lane, token class, and model, then pull configuration levers cheapest-first, one variable at a time. In the measured case, the migration that nearly shipped would have forfeited a 95% cache-hit subsidy that no price list shows.

## The patterns

- [**Pattern 3. Make silent failure loud (the dead-man's switch)**](../PATTERNS.md#3-make-silent-failure-loud-the-dead-mans-switch) — every scheduled task emits a success sentinel; a watchdog raises a finding when the sentinel is missing or stale. Self-hosted, no uptime service.
- [**Pattern 15. Price the lane before you migrate it**](../PATTERNS.md#15-price-the-lane-before-you-migrate-it) — walk the transcripts before believing any per-token price list; run each cost lever as a registered trial with a kill criterion.

Cross-reference: the always-loaded baseline and its trend alarm live in [M2](02-context-economics.md) (Pattern 9).

## Do this

Pick your one scheduled or recurring automated task (backup, digest, sync — anything unattended). Give it a sentinel: on success it writes a dated marker line to a log. Add a freshness check that runs somewhere a human actually looks — session start is the honest choice — and flags when the marker is older than the task's cadence plus slack.

**Done-check:** kill the task deliberately (disable it for a cycle) and confirm the staleness flag surfaces where you'd genuinely see it. An alarm you had to go looking for fails the check.

## Measure it

[`check_task_freshness.py`](../samples/scripts/check_task_freshness.py) is the watchdog shape; [`tier_metrics.py`](../samples/scripts/tier_metrics.py) is the lane-split spend instrument. Instrument the artefact the task produces, not the wrapper's exit code — a wrapper can exit 0 with nothing written.

Next: [M6. Provenance & delegation](06-provenance-delegation.md).
