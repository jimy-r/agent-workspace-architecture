# This repo's own workspace_check score

Scored at 34ddd30 on 2026-09-13

The README quotes an abbreviated version of this run. Pattern 16 says a claim carries its
provenance or it is a guess, so the headline number gets the same treatment as any other claim:
the commit it was measured at, the date, and the full output it was abbreviated from.

Reproduce it from a checkout of this repo:

```bash
python tools/workspace_check.py .
```

## Full output

Twelve checks, verbatim. The banner line the tool prints first echoes the local checkout path,
so it is the one line replaced here.

```text
workspace check — <repo root>

[PASS] claude-md-present — CLAUDE.md at the root, 4.7 KB (pattern 9)
[PASS] context-budget — 4.7 KB across 1 always-loaded file(s) (pattern 9)
[WARN] hooks-guard — no parseable settings file to read hooks from (pattern 7)
[WARN] permissions-floor — no permissions block in settings (pattern 4)
[FAIL] secrets-in-files — 2 hit(s): samples/tests/audit_canaries/canary.json:10 Anthropic key sk-ant-a****************, samples/tests/audit_canaries/credential_pattern_canary.md:11 Anthropic key sk-ant-a**************** (pattern 6)
[NA] env-ignored — no .env files in the tree (pattern 6)
[NA] skills-frontmatter — no .claude/skills directory (pattern 10)
[NA] agents-frontmatter — no .claude/agents directory (pattern 1)
[NA] mcp-config — no .mcp.json (pattern 6)
[PASS] duplicate-blocks — no paragraph >= 240 chars shared across 2 instruction file(s) (pattern 17)
[NA] memory-index — no MEMORY.md at the workspace root (pattern 5)

Score 6.4/10 — maturing (7 scored, 5 not applicable)
```

## Why a reference repo scores 6.4 and not 10

The linter scores a *working* workspace. This repo is a published reference, so most of what it
documents lives here as a sample rather than as live config, and the checks read the difference
honestly:

- **The three `[WARN]`s** (`settings-parse`, `hooks-guard`, `permissions-floor`) look for a live
  `.claude/settings.json` at the root. This repo ships
  [`samples/.claude/settings.example.json`](../samples/.claude/settings.example.json) instead, because a
  reference that carried a real permission floor would be handing readers someone else's allow-list.
- **The five `[NA]`s** are the same story one level down: no root `.claude/skills/`, no root
  `.claude/agents/`, no `.mcp.json`, no root `MEMORY.md`, no `.env`. Every one of them exists under
  `samples/`, where the linter does not look, because it scores the directory you point it at.
- The score is therefore a floor. It is the honest number for what sits at the root of this
  checkout, and publishing the higher number a live workspace earns would mean quoting a different
  tree than the one you can clone.

## The `secrets-in-files` FAIL is the audit canaries, and it is expected

Both hits are deliberate fixtures:

| File | Line | What it is |
|---|---|---|
| [`samples/tests/audit_canaries/canary.json`](../samples/tests/audit_canaries/canary.json) | 10 | The canary manifest's `expected_pattern` field, naming the string the audit must keep detecting. |
| [`samples/tests/audit_canaries/credential_pattern_canary.md`](../samples/tests/audit_canaries/credential_pattern_canary.md) | 11 | The canary fixture itself, a fake `ANTHROPIC_API_KEY=` line. |

Both strings carry the literal token `CANARY-FAKE-NEVER-USE`, which is there so a human reading a
credential finding can tell a fixture from a real leak at a glance. They are the known-bad inputs
described in [`samples/README.md`](../samples/README.md): a detection that stops firing on them has
regressed, so the fixtures have to stay findable.

That leaves a choice worth making in the open. Adding an exclusion for
`tests/audit_canaries/` would turn the `[FAIL]` into a `[PASS]` and raise the advertised score to
7.9/10, and it would also mean the one credential check in the linter no longer proves it can find a
credential. The check keeps its teeth and the repo keeps the lower number. A `[FAIL]` you can
explain in two lines costs less than a check you cannot trust.

If you run the linter on your own workspace and hit `secrets-in-files`, assume the opposite by
default: a hit is real until you have read the line and know why it is not.

## Keeping this current

The `self-score` job in
[`.github/workflows/validate-samples.yml`](../.github/workflows/validate-samples.yml) re-runs the
linter on every push and pull request that touches it, and fails if the `Score N/10` line no longer
matches the one recorded above. The comparison reads the score line only, so re-wording a check's
evidence text does not break the build; a change in the score does, and the fix is to re-run the
linter and update this page with a fresh commit and date.
