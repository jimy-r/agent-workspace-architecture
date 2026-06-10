---
name: audit-workthrough
description: Walk the pending audit-finding queue interactively — read scripts/_state/audit_findings.jsonl, present each pending finding with its evidence (from tasks/audit/SETUP_REVIEW.md when available), action the user's per-item decision (apply / dismiss / false-positive / defer), and mark the ledger. Invoke via "work through the audit", "/audit-workthrough", "drain audit findings", "action the audit findings". Sibling of review-queue (which drains heartbeat builds); this drains audit findings.
---

# Audit work-through

Walk the audit's pending findings one at a time and close the loop the ledger was built for: every finding ends as `accepted`, `dismissed`, or `false_positive` — never silently forgotten. This skill replaces the ad-hoc "work-through" sessions (e.g. 2026-06-04) with a repeatable ritual, and it is what feeds the R6 adaptive weighting + `[DORMANT]` source tagging their data.

## Procedure

1. **Load the queue.** Read `<workspace>/scripts/_state/audit_findings.jsonl`. Fold events per UUID (an `emit` followed by a `mark` means the mark's status wins; the latest event per UUID is authoritative). The queue = findings whose current status is `pending`, ordered newest source first.

2. **Load context.** If `<workspace>/tasks/audit/SETUP_REVIEW.md` exists, read it — it carries the full evidence text for recent findings. Older pending findings may have no surviving report text; present them from the ledger fields alone and say so.

3. **Present one finding at a time:** title, category, tier, source run, age, and the evidence paragraph from the report if found. Then ask for the decision: **apply** / **dismiss** / **false-positive** / **defer** / **skip rest**.

4. **On apply:**
   - **Verify the flagged gap against actual state FIRST** (lessons 2026-05-29 + 2026-06-04): grep/read the target file before editing. If the gap turns out to already be fixed, that is a `false_positive` mark, not an apply.
   - Make the change with normal tools, then run any validator the touched file falls under (`roles/_validate.py` for role files, `hookify` validate for settings hooks, JSON parse for settings.json).
   - Mark: `python <workspace>/scripts/audit_ledger.py mark <uuid> accepted --note "<what was done>"`.

5. **On dismiss / false-positive:** `python <workspace>/scripts/audit_ledger.py mark <uuid> dismissed|false_positive --note "<why>"`. The note matters — it is what future audits read to stop re-flagging the same shape.

6. **On defer:** leave the ledger untouched; move on.

7. **Close.** Run `python <workspace>/scripts/audit_ledger.py stats` and report a one-line summary: N actioned (X accepted / Y dismissed / Z false-positive), M still pending.

## Iron rules

- **Never mark a finding without an explicit user decision in this conversation.** Tier-3 findings exist because they need approval; this skill is the approval surface, not a bypass of it.
- One finding at a time. No batch-marking, no "accept all".
- An apply whose verification shows the gap doesn't exist is a `false_positive` — record it; that signal tunes the audit.
