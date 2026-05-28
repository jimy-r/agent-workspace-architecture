#!/usr/bin/env python3
"""
Audit cost tracking (R9) — record token usage + duration per audit run, trend
the result alongside the ghost-token baseline.

Stdlib only. Parses upgrade-audit log files in tasks/scheduled-logs/ for
known token-usage patterns and appends a per-run summary to
scripts/_state/audit_cost.jsonl.

Based on the OpenSSF Scorecard cost-discipline principle (independent fast
checks beat deep multi-step investigations) and pairs with the ghost-token
counter (scripts/ghost_token_counter.py) as a budget-awareness loop. See
`Reference/Research/2026-05-28_audit-upgrade-best-practices.md` §5
Audit depth vs audit cost.

CLI:
  log [--all]              record cost for most recent (or all) audit run(s)
  trend [--weeks 8]        print a per-run table over the window
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
LOGS_DIR = WORKSPACE / "tasks" / "scheduled-logs"
COST_LOG = WORKSPACE / "scripts" / "_state" / "audit_cost.jsonl"

# These regexes match the patterns emitted by claude --print's session summary
# and the audit's own progress reporting. Multiple patterns are tried; first
# match wins.
TOKEN_PATTERNS = [
    re.compile(r"total[_\s]*tokens?[:\s]+(\d[\d,]*)", re.IGNORECASE),
    re.compile(r"(\d[\d,]*)\s*total\s*tokens", re.IGNORECASE),
    re.compile(r"context[:\s]+(\d[\d,]*)\s*tokens?", re.IGNORECASE),
]
DURATION_PATTERNS = [
    re.compile(r"duration[:\s]+(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*seconds?", re.IGNORECASE),
]
SENTINEL_OK = "UPGRADE_AUDIT_OK"
SENTINEL_FAIL = "UPGRADE_AUDIT_FAILED"
LOG_PATTERN = re.compile(
    r"^upgrade-audit_(?P<date>\d{4}-\d{2}-\d{2})-(?P<time>\d{4})\.log$"
)


def parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_log(log: Path) -> dict:
    """Extract a cost record from a single upgrade-audit log."""
    body = log.read_text(encoding="utf-8", errors="replace")
    match = LOG_PATTERN.match(log.name)
    started_at = None
    if match:
        started_at = f"{match.group('date')}T{match.group('time')[:2]}:{match.group('time')[2:]}:00"

    tokens = None
    for pattern in TOKEN_PATTERNS:
        m = pattern.search(body)
        if m:
            tokens = parse_int(m.group(1))
            break

    duration = None
    for pattern in DURATION_PATTERNS:
        m = pattern.search(body)
        if m:
            duration = float(m.group(1))
            break

    status = (
        "ok"
        if SENTINEL_OK in body
        else ("failed" if SENTINEL_FAIL in body else "unknown")
    )

    return {
        "log": log.name,
        "started_at": started_at,
        "tokens": tokens,
        "duration_seconds": duration,
        "status": status,
        "size_bytes": log.stat().st_size,
    }


def find_audit_logs() -> list[Path]:
    if not LOGS_DIR.is_dir():
        return []
    return sorted(
        (
            entry
            for entry in LOGS_DIR.iterdir()
            if entry.is_file() and LOG_PATTERN.match(entry.name)
        ),
        key=lambda p: p.name,
    )


def already_logged() -> set[str]:
    if not COST_LOG.exists():
        return set()
    seen = set()
    with COST_LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                seen.add(rec.get("log", ""))
            except json.JSONDecodeError:
                continue
    return seen


def append_record(record: dict) -> None:
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def cmd_log(args: argparse.Namespace) -> int:
    logs = find_audit_logs()
    if not logs:
        print("no upgrade-audit logs found", file=sys.stderr)
        return 1
    if not args.all:
        logs = logs[-1:]
    seen = already_logged()
    added = 0
    for log in logs:
        if log.name in seen and not args.force:
            continue
        record = parse_log(log)
        append_record(record)
        added += 1
        print(
            f"recorded {log.name}: tokens={record['tokens']} "
            f"duration={record['duration_seconds']}s status={record['status']}"
        )
    print(f"appended {added} new record(s)")
    return 0


def cmd_trend(args: argparse.Namespace) -> int:
    if not COST_LOG.exists():
        print("no cost log yet", file=sys.stderr)
        return 1
    since = dt.datetime.now() - dt.timedelta(weeks=args.weeks)
    rows = []
    with COST_LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not rec.get("started_at"):
                continue
            try:
                started = dt.datetime.fromisoformat(rec["started_at"])
            except ValueError:
                continue
            if started < since:
                continue
            rows.append(rec)
    if not rows:
        print(f"no records in last {args.weeks} weeks")
        return 0
    rows.sort(key=lambda r: r.get("started_at", ""))
    print(f"{'started':<19}  {'status':<8}  {'tokens':>9}  {'dur(s)':>7}")
    print("-" * 50)
    for rec in rows:
        tok = f"{rec['tokens']:,}" if rec["tokens"] else "-"
        dur = f"{rec['duration_seconds']:.1f}" if rec["duration_seconds"] else "-"
        print(f"{rec['started_at']:<19}  {rec['status']:<8}  {tok:>9}  {dur:>7}")
    # Trend summary
    with_tokens = [r["tokens"] for r in rows if r["tokens"]]
    if len(with_tokens) >= 2:
        median = sorted(with_tokens)[len(with_tokens) // 2]
        latest = with_tokens[-1]
        delta = ((latest - median) / median) * 100 if median else 0
        print()
        print(f"latest vs median: {latest:,} vs {median:,} ({delta:+.1f}%)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_log = sub.add_parser("log", help="record cost for most recent audit log")
    p_log.add_argument(
        "--all", action="store_true", help="record cost for all logs not yet seen"
    )
    p_log.add_argument(
        "--force", action="store_true", help="re-record even if already seen"
    )
    p_log.set_defaults(func=cmd_log)

    p_trend = sub.add_parser("trend", help="print per-run table")
    p_trend.add_argument("--weeks", type=int, default=8)
    p_trend.set_defaults(func=cmd_trend)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
