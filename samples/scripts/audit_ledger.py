#!/usr/bin/env python3
"""
Audit finding ledger (R3) — append-only JSONL of every audit finding with
acceptance status tracking.

Each finding emitted by the audit gets a UUID, category, tier, and lives in
the ledger thereafter. As the user actions findings (or rejects them), the
status is updated. The audit reads back accept-rate per category to weight
future findings.

Based on the "opposing-metric pair" principle (Manheim on metric gaming) and
the alert-fatigue mitigation literature (ACM Computing Surveys 2025,
DOI:10.1145/3723158). See `Reference/Research/2026-05-28_audit-upgrade-best-practices.md`
§4 Gap 6 + §3 Alert Fatigue.

Stdlib only.

CLI subcommands:
  emit  --category C --tier T --title S [--source SOURCE]   -> prints UUID
  mark  UUID STATUS [--note NOTE]                            -> updates status
  stats [--category C] [--since YYYY-MM-DD]                  -> accept-rate report
  recent [--n 20]                                            -> last N findings
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import uuid
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
LEDGER = WORKSPACE / "scripts" / "_state" / "audit_findings.jsonl"

VALID_TIERS = {"1", "2", "3", "critical"}
VALID_STATUSES = {"pending", "accepted", "dismissed", "superseded", "false_positive"}


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def append(record: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def read_all() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    with LEDGER.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def latest_state() -> dict[str, dict]:
    """Replay the ledger; return the latest record per finding UUID."""
    state: dict[str, dict] = {}
    for record in read_all():
        fid = record.get("uuid")
        if not fid:
            continue
        state[fid] = record
    return state


def cmd_emit(args: argparse.Namespace) -> int:
    if args.tier not in VALID_TIERS:
        print(
            f"invalid tier: {args.tier} (valid: {sorted(VALID_TIERS)})", file=sys.stderr
        )
        return 2
    fid = str(uuid.uuid4())
    record = {
        "event": "emit",
        "uuid": fid,
        "ts": now_iso(),
        "category": args.category,
        "tier": args.tier,
        "title": args.title,
        "source": args.source or "audit",
        "status": "pending",
    }
    append(record)
    print(fid)
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUSES:
        print(
            f"invalid status: {args.status} (valid: {sorted(VALID_STATUSES)})",
            file=sys.stderr,
        )
        return 2
    state = latest_state()
    if args.uuid not in state:
        print(f"unknown UUID: {args.uuid}", file=sys.stderr)
        return 2
    prior = state[args.uuid]
    record = {
        "event": "mark",
        "uuid": args.uuid,
        "ts": now_iso(),
        "category": prior["category"],
        "tier": prior["tier"],
        "title": prior["title"],
        "source": prior.get("source", "audit"),
        "status": args.status,
        "note": args.note,
    }
    append(record)
    print(f"marked {args.uuid} -> {args.status}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    state = latest_state()
    if args.since:
        try:
            since = dt.datetime.fromisoformat(args.since)
        except ValueError:
            print(f"invalid --since date: {args.since}", file=sys.stderr)
            return 2
        state = {
            uid: rec
            for uid, rec in state.items()
            if dt.datetime.fromisoformat(rec["ts"]) >= since
        }

    by_category: dict[str, dict[str, int]] = {}
    for rec in state.values():
        cat = rec["category"]
        if args.category and cat != args.category:
            continue
        if cat not in by_category:
            by_category[cat] = {s: 0 for s in VALID_STATUSES}
        by_category[cat][rec["status"]] += 1

    if not by_category:
        print("no findings match filter")
        return 0

    width = max(len(c) for c in by_category)
    header = f"{'category':<{width}}  pend  acc  dism  sup   fp   accept-rate"
    print(header)
    print("-" * len(header))
    for cat in sorted(by_category):
        counts = by_category[cat]
        total_resolved = (
            counts["accepted"] + counts["dismissed"] + counts["false_positive"]
        )
        accept_rate = counts["accepted"] / total_resolved if total_resolved > 0 else 0.0
        rate_display = f"{accept_rate * 100:.0f}%" if total_resolved > 0 else "  -"
        print(
            f"{cat:<{width}}  {counts['pending']:>4}  {counts['accepted']:>3}  "
            f"{counts['dismissed']:>4}  {counts['superseded']:>3}  "
            f"{counts['false_positive']:>3}   {rate_display:>5}"
        )
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    state = latest_state()
    items = sorted(state.values(), key=lambda r: r["ts"], reverse=True)[: args.n]
    for rec in items:
        title = rec["title"][:60]
        print(
            f"{rec['ts']}  [{rec['tier']}] [{rec['status']:>11}] {rec['category']}: {title}"
        )
    return 0


def cmd_category_weight(args: argparse.Namespace) -> int:
    """Emit a 0.0-1.0 weight per category based on historical accept rate.
    Used by audit Phase 2.5b adaptive weighting (R6)."""
    state = latest_state()
    weights: dict[str, float] = {}
    counts: dict[str, dict[str, int]] = {}
    for rec in state.values():
        cat = rec["category"]
        counts.setdefault(cat, {s: 0 for s in VALID_STATUSES})
        counts[cat][rec["status"]] += 1
    for cat, c in counts.items():
        total_resolved = c["accepted"] + c["dismissed"] + c["false_positive"]
        if total_resolved < 3:
            weights[cat] = 1.0  # not enough data; full weight
        else:
            weights[cat] = max(0.2, c["accepted"] / total_resolved)
    print(json.dumps(weights, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_emit = sub.add_parser("emit", help="append a new finding")
    p_emit.add_argument(
        "--category",
        required=True,
        help="e.g. Security/Credentials, Setup/Hooks, External/Plugins",
    )
    p_emit.add_argument("--tier", required=True, choices=sorted(VALID_TIERS))
    p_emit.add_argument("--title", required=True, help="short human-readable title")
    p_emit.add_argument("--source", help="audit run id or other origin tag")
    p_emit.set_defaults(func=cmd_emit)

    p_mark = sub.add_parser("mark", help="update finding status")
    p_mark.add_argument("uuid", help="finding UUID")
    p_mark.add_argument("status", choices=sorted(VALID_STATUSES))
    p_mark.add_argument("--note", help="optional reason")
    p_mark.set_defaults(func=cmd_mark)

    p_stats = sub.add_parser("stats", help="acceptance-rate by category")
    p_stats.add_argument("--category", help="filter to one category")
    p_stats.add_argument(
        "--since", help="ISO date / datetime — only count records on/after"
    )
    p_stats.set_defaults(func=cmd_stats)

    p_recent = sub.add_parser("recent", help="last N findings")
    p_recent.add_argument("--n", type=int, default=20)
    p_recent.set_defaults(func=cmd_recent)

    p_weight = sub.add_parser(
        "category-weight", help="emit JSON weights per category for adaptive sampling"
    )
    p_weight.set_defaults(func=cmd_category_weight)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
