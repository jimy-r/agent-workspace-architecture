#!/usr/bin/env python3
"""Token Budget module — measurement CLI (2026-06-10).

Wraps ccusage (via npx) to report Claude Code token usage and persist a daily
history for trend analysis. Costs are API-EQUIVALENT dollars computed from
local transcripts — on a subscription they represent plan-usage value, not
billed spend. From 2026-06-15 headless `claude -p` draws from a capped monthly
credit pool at API rates, so the same numbers become directly financial for
every scheduled task.

Subcommands:
  report      last-7-days table + totals + cache-hit rate + quiet-day floor
  log         append a per-day summary to scripts/_state/token_history.jsonl
              (idempotent per date; defaults to yesterday)
  brief-line  ONE line for the morning brief. Never raises — prints a
              fallback string on any error so the brief can't be aborted
              by a measurement failure.
  trend       weekly averages from the persisted history

Owner doc for the Token Budget module: META_ARCHITECTURE.md §2 (Token Budget row). Best-practice collection (the module's substance, read by the audit's
G1 rotation): the workspace's token-optimisation best-practice brief.
Sibling instruments: ghost_token_counter.py (always-loaded context),
audit_cost.py (per-audit-run), heartbeat/preflight_gate.py (spend avoidance).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
HISTORY = WORKSPACE / "scripts" / "_state" / "token_history.jsonl"
NPX_TIMEOUT_S = 180


def _npx() -> str:
    for name in ("npx.cmd", "npx"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError("npx not found on PATH (needed for ccusage)")


def _ccusage_daily(since: dt.date) -> list[dict]:
    cmd = [
        _npx(),
        "-y",
        "ccusage@latest",
        "daily",
        "--json",
        "--since",
        since.strftime("%Y%m%d"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=NPX_TIMEOUT_S)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ccusage exit {proc.returncode}: {proc.stderr.strip()[:200]}"
        )
    payload = json.loads(proc.stdout)
    rows = payload.get("daily") or payload.get("data") or []
    # ccusage emits one row per agent per day plus an "all" aggregate; keep
    # only the aggregate (or rows with no agent field at all).
    rows = [r for r in rows if r.get("agent") in (None, "all")]
    return [_normalise(row) for row in rows]


def _pick(row: dict, *names, default=0):
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _normalise(row: dict) -> dict:
    input_t = _pick(row, "inputTokens", "input_tokens")
    output_t = _pick(row, "outputTokens", "output_tokens")
    cache_w = _pick(
        row, "cacheCreationTokens", "cache_creation_tokens", "cacheCreateTokens"
    )
    cache_r = _pick(row, "cacheReadTokens", "cache_read_tokens")
    denom = input_t + cache_w + cache_r
    # ccusage names the day field "period" (e.g. "2026-06-08"); older builds
    # used "date". Truncate to the YYYY-MM-DD prefix either way.
    return {
        "date": str(_pick(row, "period", "date", default=""))[:10],
        "input": input_t,
        "output": output_t,
        "cache_create": cache_w,
        "cache_read": cache_r,
        "total_cost": round(
            float(_pick(row, "totalCost", "total_cost", default=0.0)), 2
        ),
        "cache_hit_rate": round(cache_r / denom, 3) if denom else None,
        "models": _pick(row, "modelsUsed", "models_used", "models", default=[]),
    }


def _load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    records = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def cmd_report(days: int) -> int:
    since = dt.date.today() - dt.timedelta(days=days)
    rows = _ccusage_daily(since)
    if not rows:
        print("no usage rows returned")
        return 1
    print(f"Token usage (API-equivalent $) — since {since.isoformat()}")
    print(f"{'date':<12}{'$equiv':>9}{'cache-hit':>11}{'output':>12}")
    for row in rows:
        hit = (
            f"{row['cache_hit_rate']:.0%}"
            if row["cache_hit_rate"] is not None
            else "n/a"
        )
        print(
            f"{row['date']:<12}{row['total_cost']:>9.2f}{hit:>11}{row['output']:>12,}"
        )
    costs = [r["total_cost"] for r in rows]
    print(
        f"\ntotal ${sum(costs):.2f}   avg ${sum(costs) / len(costs):.2f}/day   "
        f"quiet-day floor ~${min(costs):.2f}/day (scheduled-baseline estimate)"
    )
    return 0


def cmd_log(date_str: str | None) -> int:
    target = (
        dt.date.fromisoformat(date_str)
        if date_str
        else dt.date.today() - dt.timedelta(days=1)
    )
    history = _load_history()
    if any(rec.get("date") == target.isoformat() for rec in history):
        print(f"already logged {target.isoformat()}")
        return 0
    rows = _ccusage_daily(target)
    row = next((r for r in rows if r["date"] == target.isoformat()), None)
    if row is None:
        print(f"no usage data for {target.isoformat()}")
        return 1
    row["logged_at"] = dt.datetime.now().isoformat(timespec="seconds")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"logged {target.isoformat()}: ${row['total_cost']:.2f} equiv")
    return 0


def cmd_brief_line() -> int:
    """One line for the morning brief. Never raises, never exits non-zero."""
    try:
        since = dt.date.today() - dt.timedelta(days=8)
        rows = _ccusage_daily(since)
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        y_row = next((r for r in rows if r["date"] == yesterday), None)
        week = [r for r in rows if r["date"] != dt.date.today().isoformat()][-7:]
        avg = sum(r["total_cost"] for r in week) / len(week) if week else 0.0
        if y_row:
            hit = (
                f"{y_row['cache_hit_rate']:.0%}"
                if y_row["cache_hit_rate"] is not None
                else "n/a"
            )
            print(
                f"Token spend yesterday: ${y_row['total_cost']:.2f} API-equiv "
                f"(7-day avg ${avg:.2f}/day; cache-hit {hit})."
            )
        else:
            print(f"Token spend yesterday: no data (7-day avg ${avg:.2f}/day).")
    except Exception:
        print("Token spend: unavailable this run.")
    return 0


def cmd_trend(weeks: int) -> int:
    history = sorted(_load_history(), key=lambda r: r.get("date", ""))
    if not history:
        print(
            "no history yet — run `token_report.py log` daily (the morning brief does)"
        )
        return 1
    buckets: dict[str, list[float]] = {}
    for rec in history:
        try:
            day = dt.date.fromisoformat(rec["date"])
        except (KeyError, ValueError):
            continue
        key = f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"
        buckets.setdefault(key, []).append(rec.get("total_cost", 0.0))
    for key in sorted(buckets)[-weeks:]:
        vals = buckets[key]
        print(
            f"{key}: avg ${sum(vals) / len(vals):.2f}/day over {len(vals)} logged days"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="last-N-days usage table")
    p_report.add_argument("--days", type=int, default=7)
    p_log = sub.add_parser("log", help="append one day to token_history.jsonl")
    p_log.add_argument("--date", help="ISO date; default yesterday")
    sub.add_parser("brief-line", help="one fail-safe line for the morning brief")
    p_trend = sub.add_parser("trend", help="weekly averages from history")
    p_trend.add_argument("--weeks", type=int, default=8)
    args = parser.parse_args()

    if args.cmd == "report":
        return cmd_report(args.days)
    if args.cmd == "log":
        return cmd_log(args.date)
    if args.cmd == "brief-line":
        return cmd_brief_line()
    if args.cmd == "trend":
        return cmd_trend(args.weeks)
    return 2


if __name__ == "__main__":
    sys.exit(main())
