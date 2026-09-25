---
name: upgrade-audit
description: MANUAL (no scheduled task exists) -- run the full audit agent. Invoked by the user inside the desktop app (scripts/audit.bat remains a valid alternate path). Phases are defined ONLY by the canonical instructions -- this file must not enumerate them (its list drifted: named the stripped Phase 2.5c, omitted Phases 0/2.6b/2.9; finding d2eaa65b). Canonical instructions in <workspace>/.claude/agents/audit.md.
---

# Upgrade audit cycle

You are firing as the `upgrade-audit` lane. This lane is MANUAL and is normally invoked by the user inside the DESKTOP APP (`scripts/audit.bat` still works but is not the usual path), NOT by Windows Task Scheduler -- no scheduled task for it has ever existed (verified 2026-08-26). The dead-man switch tracks it as a manual lane with a 14-day staleness threshold, so a CRITICAL from it means the audit has not been RUN, not that a schedule broke. Dispatch the `audit` subagent.

Use the Agent tool with `subagent_type: audit` and this prompt:

> Run the full weekly upgrade audit on the <workspace> workspace per the canonical instructions at `<workspace>/.claude/agents/audit.md`. Cover ALL phases exactly as the canonical instructions define them, including the check-phases (0, 2.6b, 2.9) -- the phase list lives in audit.md ONLY, and any enumeration here is presumed stale (finding d2eaa65b: this file named a phase stripped 2026-05-23).
>
> Carry-forward check: read the prior week's CRITICAL items from the existing Setup Review block and verify each has been resolved. Unresolved CRITICALs carry forward to this week's findings (marked "carried — unresolved").
>
> Auto-apply: enabled per `audit.md` tier rules. Tier-3 findings require user approval and must be lodged as bullets in the Setup Review / Security blocks rather than auto-applied. Tier-1/Tier-2 auto-applies (≤5 per run) must be enumerated under "Files modified this run".

When the audit subagent returns, print its summary verbatim (tier counts, top 3 findings, files modified). Then print `UPGRADE_AUDIT_OK` on a final line if no fatal errors. If the subagent reports a fatal error (e.g. auth failure), surface it clearly and do NOT print the sentinel — the wrapper will mark the cycle failed.

Note: this skill is *also* invoked manually via `<workspace>/scripts/audit.bat`; the audit agent itself is the single source of truth and the same regardless of invocation path.
