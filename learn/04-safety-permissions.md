# M4. Safety & permissions — cheap mechanical guards

> [Learn track](README.md) · dimension: **Safety & permissions** in the [maturity check](https://jamesross.ai/tools/maturity-check?utm_source=github&utm_medium=repo&utm_campaign=learn-track).

After this you can make each guard block on demand and tell, from the message, which hook did the blocking.

"Be more careful" does not scale to an agent that runs hundreds of tool calls a day. What scales is a small set of deterministic guards that intercept the casual failure modes — an output redirect over your `.env`, a force-push, a delete aimed one folder too high — before they run. The guards are mistake-catchers, not security boundaries: a determined process writing files from inside Python is out of scope, and that honesty matters, because a guard you believe is a boundary is worse than no guard.

The companion instinct is routing by consequence. Decide what may happen automatically by what an action *costs if wrong* — mechanical reversibility — never by how confident the request sounds. And keep the one class of damage no hook can undo, leaked credentials, out of files entirely.

## The patterns

- [**Pattern 7. A cheap hook beats a careful agent**](../PATTERNS.md#p7) — a pre-execution hook string-matches tool calls against a blocklist and fails open; a ten-line check catches most accidental damage for almost nothing.
- [**Pattern 4. Tier by mechanical impact, not by tone**](../PATTERNS.md#p4) — auto-apply the trivially reversible; human-gate anything that deletes, publishes, or spends.
- [**Pattern 6. Credentials live in one place, never in files**](../PATTERNS.md#p6) — a password manager is the single store; files carry item *names*; runtime resolves values and scrubs them.

## Do this

Install the two guards from the [starter template](https://github.com/jimy-r/agent-workspace-starter?utm_source=github&utm_medium=repo&utm_campaign=learn-track) (or wire your own equivalents): the file-protection hook and the bash-command hook, plus a `protected-paths.txt` naming what the agent must never write. Then **live-fire them**: ask the agent to append a line to a protected test file, and to push to a protected branch of a scratch repo. Watch both get blocked.

Both attempts should come back refused, with the hook's reason passed back to the agent. With the starter's hooks the edit is refused by a message that begins `Edit/Write blocked:` and names the matching entry in `protected-paths.txt`. The push is refused by a line that begins `[bash-guard] BLOCKED:`. Afterwards the test file is unchanged and the scratch remote has no new commit.

**Done-check:** two deliberate violations attempted, two blocks observed. A hook that has never fired on a known-bad input is configuration, not protection.

Record it: tick the module on the [track checklist](README.md#track-your-progress), or post the output in [Show and tell](https://github.com/jimy-r/agent-workspace-architecture/discussions/categories/show-and-tell) where the next reader can compare.

## Measure it

The live-fire *is* the measurement — repeat it whenever the hook config changes. For the credential rule, grep your workspace for anything shaped like a secret (`sk-`, `token`, `Bearer`): the count should be zero values, any number of item names.

Expect noise, since `token` matches plenty of ordinary prose. Read each hit. A line that names an item in the password manager or an environment variable passes, and a line where the secret itself follows the match is the finding.

## If it didn't work

- The edit went through. Check that the test file's name is in `.claude/protected-paths.txt`, because the hook blocks only paths that contain a listed substring. Then check that the hook is wired in `.claude/settings.json` and that the `python3` it calls runs in your shell. Both hooks fail open, so an error inside one lets the call through.
- Both blocks carry the `[bash-guard]` prefix. The agent appended with a shell redirect, so the bash guard caught both attempts and the file-protection hook hasn't fired yet. Ask for the change through the edit tool and look for `Edit/Write blocked:`.
- The push went through. The starter's guard refuses a push that names `main` or `master`, and any force push. It matches the command's text, so a bare `git push` or a push to a branch with another name passes.
- The grep turned up a real secret. Treat it as leaked. Rotate it, then keep the new value in the password manager and only the item name in the file.

---

*Next: [M5. Telemetry & cost](05-telemetry-cost.md) · Stuck, or done? [Discussions](https://github.com/jimy-r/agent-workspace-architecture/discussions) · New modules, teardowns and tools: [Agent Workspaces](https://jimyr.substack.com)*
