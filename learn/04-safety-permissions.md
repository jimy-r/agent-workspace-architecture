# M4. Safety & permissions — cheap mechanical guards

> [Learn track](README.md) · dimension: **Safety & permissions** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

"Be more careful" does not scale to an agent that runs hundreds of tool calls a day. What scales is a small set of deterministic guards that intercept the casual failure modes — an output redirect over your `.env`, a force-push, a delete aimed one folder too high — before they run. The guards are mistake-catchers, not security boundaries: a determined process writing files from inside Python is out of scope, and that honesty matters, because a guard you believe is a boundary is worse than no guard.

The companion instinct is routing by consequence. Decide what may happen automatically by what an action *costs if wrong* — mechanical reversibility — never by how confident the request sounds. And keep the one class of damage no hook can undo, leaked credentials, out of files entirely.

## The patterns

- [**Pattern 7. A cheap hook beats a careful agent**](../PATTERNS.md#7-a-cheap-hook-beats-a-careful-agent) — a pre-execution hook string-matches tool calls against a blocklist and fails open; a ten-line check catches most accidental damage for almost nothing.
- [**Pattern 4. Tier by mechanical impact, not by tone**](../PATTERNS.md#4-tier-by-mechanical-impact-not-by-tone) — auto-apply the trivially reversible; human-gate anything that deletes, publishes, or spends.
- [**Pattern 6. Credentials live in one place, never in files**](../PATTERNS.md#6-credentials-live-in-one-place-never-in-files) — a password manager is the single store; files carry item *names*; runtime resolves values and scrubs them.

## Do this

Install the two guards from the [starter template](https://github.com/jimy-r/agent-workspace-starter?utm_source=github&utm_medium=repo&utm_campaign=learn-track) (or wire your own equivalents): the file-protection hook and the bash-command hook, plus a `protected-paths.txt` naming what the agent must never write. Then **live-fire them**: ask the agent to append a line to a protected test file, and to push to a protected branch of a scratch repo. Watch both get blocked.

**Done-check:** two deliberate violations attempted, two blocks observed. A hook that has never fired on a known-bad input is configuration, not protection.

## Measure it

The live-fire *is* the measurement — repeat it whenever the hook config changes. For the credential rule, grep your workspace for anything shaped like a secret (`sk-`, `token`, `Bearer`): the count should be zero values, any number of item names.

Next: [M5. Telemetry & cost](05-telemetry-cost.md).
