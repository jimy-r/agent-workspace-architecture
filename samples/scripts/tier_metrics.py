#!/usr/bin/env python3
# Redacted sample from the private workspace - see PATTERNS.md Pattern 15
# ("Price the lane before you migrate it"). Measures a token-management
# intervention set: lane split, cache-hit, model adoption, rework markers.
# Adapt TRANSCRIPT_ROOT, INTERVENTION_DATE, and the FLAG thresholds to yours.
"""Read-only measurement instrument for the 2026-08-13 token-management
interventions (ultracode default off, differentiated effort map, Fable to
Sonnet execution trial).

INTERVENTION_DATE marks the day those interventions landed: rows/transcript
activity on or after it are "post", the 28 days before it are "baseline".

Computes four things:
  1. Spend trend      - token_history.jsonl daily $ before/after the date.
  2. Lane split        - main vs subagent-lane transcript cost share, the
                          subagent lane's cache-hit rate, and Sonnet-adoption
                          share (cost by model family) within that lane.
  3. Rework markers     - "SONNET-REWORK" occurrences in tasks/todo.md against
                          subagent-lane Sonnet DISPATCHES (one transcript file
                          = one task; the 20% kill criterion is per task).
  4. Assessment          - PASS / FLAG / INFO verdicts on the four checks
                          above (sonnet-adoption, rework-rate, spend-trend,
                          cache-hit). Advisory only: never exits non-zero for
                          a FLAG, only for a --selftest failure or a crash.

Never writes anything. scripts/audit_checks/run_all.py consumes this tool's
`--json` output as the data source for its own check_tier_trial_metrics.

Usage:
  python scripts/tier_metrics.py               human-readable report
  python scripts/tier_metrics.py --json        machine-readable dict on stdout
  python scripts/tier_metrics.py --days N      analysis window (default 14)
  python scripts/tier_metrics.py --selftest    built-in asserts, PASS/FAIL count
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
import time
from pathlib import Path

INTERVENTION_DATE = "2026-08-13"  # set to the date YOUR interventions landed
WORKSPACE = Path(__file__).resolve().parents[1]
TOKEN_HISTORY_PATH = WORKSPACE / "scripts" / "_state" / "token_history.jsonl"
TODO_PATH = WORKSPACE / "tasks" / "todo.md"
# Point this at your own project transcript directory under ~/.claude/projects/
TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects" / "YOUR-PROJECT-DIR"

# $ per million tokens, (input_rate, output_rate). Family matched by substring
# on the model string. Cache pricing is a multiple of the family input rate:
# cache_creation bills at 1.25x, cache_read at 0.1x (both spec'd, not derived).
FAMILY_RATES = {
    "fable": (10.0, 50.0),
    "opus": (5.0, 25.0),
    "sonnet": (3.0, 15.0),
    "haiku": (1.0, 5.0),
}


def family_of(model: str | None) -> str:
    m = (model or "").lower()
    for fam in ("fable", "opus", "sonnet", "haiku"):
        if fam in m:
            return fam
    return "unknown"


def price_per_million(model: str | None) -> tuple[float, float]:
    return FAMILY_RATES.get(family_of(model), FAMILY_RATES["opus"])


def cost_of_usage(usage: dict, model: str | None) -> float:
    in_rate, out_rate = price_per_million(model)
    input_tok = usage.get("input_tokens") or 0
    cache_creation = usage.get("cache_creation_input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    output_tok = usage.get("output_tokens") or 0
    return (
        input_tok * in_rate
        + cache_creation * in_rate * 1.25
        + cache_read * in_rate * 0.1
        + output_tok * out_rate
    ) / 1_000_000


def classify_lane(path: str) -> str:
    return "subagent" if "subagents" in Path(path).parts else "main"


def extract_usage(obj: dict) -> tuple[str | None, dict | None]:
    message = obj.get("message")
    if isinstance(message, dict):
        usage = message.get("usage")
        if isinstance(usage, dict):
            return message.get("model"), usage
    usage = obj.get("usage")
    if isinstance(usage, dict):
        return None, usage
    return None, None


def _zero_bucket() -> dict:
    return {"cost": 0.0, "input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}


def load_token_history(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except (ValueError, TypeError):
                    continue
    except OSError:
        return []
    return rows


def spend_trend(rows: list[dict], intervention_date: str = INTERVENTION_DATE) -> dict:
    post_vals = [
        r["total_cost"]
        for r in rows
        if isinstance(r.get("date"), str)
        and r["date"] >= intervention_date
        and isinstance(r.get("total_cost"), (int, float))
    ]
    base_start = (
        dt.date.fromisoformat(intervention_date) - dt.timedelta(days=28)
    ).isoformat()
    base_end = (
        dt.date.fromisoformat(intervention_date) - dt.timedelta(days=1)
    ).isoformat()
    baseline_vals = [
        r["total_cost"]
        for r in rows
        if isinstance(r.get("date"), str)
        and base_start <= r["date"] <= base_end
        and isinstance(r.get("total_cost"), (int, float))
    ]
    return {
        "post_avg": statistics.mean(post_vals) if post_vals else None,
        "baseline_median": statistics.median(baseline_vals) if baseline_vals else None,
        "post_n": len(post_vals),
        "baseline_n": len(baseline_vals),
    }


def iter_recent_transcripts(
    root: Path, days: int, now: float | None = None
) -> list[Path]:
    now = time.time() if now is None else now
    cutoff = now - days * 86400
    if not root.is_dir():
        return []
    out = []
    for p in root.rglob("*.jsonl"):
        try:
            if p.stat().st_mtime >= cutoff:
                out.append(p)
        except OSError:
            continue
    return out


def build_lane_stats(files: list[Path]) -> dict:
    totals = {"main": _zero_bucket(), "subagent": _zero_bucket()}
    family_cost = {
        "fable": 0.0,
        "opus": 0.0,
        "sonnet": 0.0,
        "haiku": 0.0,
        "unknown": 0.0,
    }
    active_days_post: set[str] = set()
    sonnet_calls_subagent = 0
    sonnet_dispatches_subagent = 0

    for path in files:
        lane = classify_lane(str(path))
        file_has_sonnet = False
        try:
            fh = path.open("r", encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                model, usage = extract_usage(obj)
                if usage is None:
                    continue
                cost = cost_of_usage(usage, model)
                bucket = totals[lane]
                bucket["cost"] += cost
                bucket["input"] += int(usage.get("input_tokens") or 0)
                bucket["cache_creation"] += int(
                    usage.get("cache_creation_input_tokens") or 0
                )
                bucket["cache_read"] += int(usage.get("cache_read_input_tokens") or 0)
                bucket["output"] += int(usage.get("output_tokens") or 0)
                if lane == "subagent":
                    fam = family_of(model)
                    family_cost[fam] = family_cost.get(fam, 0.0) + cost
                    if fam == "sonnet":
                        sonnet_calls_subagent += 1
                        file_has_sonnet = True
                    ts = obj.get("timestamp")
                    if (
                        isinstance(ts, str)
                        and len(ts) >= 10
                        and ts[:10] >= INTERVENTION_DATE
                    ):
                        active_days_post.add(ts[:10])
        if lane == "subagent" and file_has_sonnet:
            sonnet_dispatches_subagent += 1

    total_cost = totals["main"]["cost"] + totals["subagent"]["cost"]
    cost_share_pct = {
        name: (totals[name]["cost"] / total_cost * 100.0) if total_cost > 0 else 0.0
        for name in ("main", "subagent")
    }
    sub = totals["subagent"]
    denom = sub["cache_read"] + sub["input"] + sub["cache_creation"]
    subagent_cache_hit_rate = (sub["cache_read"] / denom) if denom > 0 else None
    sub_cost = sub["cost"]
    subagent_family_share_pct = {
        fam: (cost / sub_cost * 100.0) if sub_cost > 0 else 0.0
        for fam, cost in family_cost.items()
    }

    return {
        "main": totals["main"],
        "subagent": totals["subagent"],
        "cost_share_pct": cost_share_pct,
        "subagent_cache_hit_rate": subagent_cache_hit_rate,
        "subagent_family_cost": family_cost,
        "subagent_family_share_pct": subagent_family_share_pct,
        "active_days_post": len(active_days_post),
        "files_scanned": len(files),
        "sonnet_calls_subagent": sonnet_calls_subagent,
        "sonnet_dispatches_subagent": sonnet_dispatches_subagent,
    }


def compute_rework(todo_path: Path, sonnet_dispatches: int, sonnet_calls: int) -> dict:
    # The 20% kill criterion is per TASK; one dispatched subagent transcript
    # file = one task, so dispatches (not API calls) are the denominator.
    try:
        markers = todo_path.read_text(encoding="utf-8", errors="ignore").count(
            "SONNET-REWORK"
        )
    except OSError:
        markers = 0
    ratio = (markers / sonnet_dispatches) if sonnet_dispatches > 0 else None
    return {
        "markers": markers,
        "sonnet_dispatches": sonnet_dispatches,
        "sonnet_calls": sonnet_calls,
        "ratio": ratio,
    }


def assess(spend: dict, lane: dict, rework: dict) -> list[dict]:
    out = []

    sub_cost = lane["subagent"]["cost"]
    sonnet_cost = lane["subagent_family_cost"].get("sonnet", 0.0)
    sonnet_share = (sonnet_cost / sub_cost) if sub_cost > 0 else 0.0
    active_days_post = lane["active_days_post"]
    if active_days_post >= 3 and sonnet_share == 0.0:
        out.append(
            {
                "check": "sonnet-adoption",
                "status": "FLAG",
                "detail": f"{active_days_post} active subagent-lane day(s) after {INTERVENTION_DATE}, "
                f"sonnet share of subagent-lane cost = 0% (trial decided but not running)",
            }
        )
    else:
        out.append(
            {
                "check": "sonnet-adoption",
                "status": "PASS",
                "detail": f"sonnet share of subagent-lane cost = {sonnet_share:.1%} "
                f"over {active_days_post} active day(s) post-intervention",
            }
        )

    markers, denom, ratio = (
        rework["markers"],
        rework["sonnet_dispatches"],
        rework["ratio"],
    )
    if markers == 0 and denom == 0:
        out.append(
            {
                "check": "rework-rate",
                "status": "INFO",
                "detail": "no SONNET-REWORK markers and no subagent-lane sonnet dispatches in window",
            }
        )
    elif ratio is None and markers >= 3:
        out.append(
            {
                "check": "rework-rate",
                "status": "FLAG",
                "detail": f"{markers} SONNET-REWORK marker(s), 0 subagent-lane sonnet dispatches to normalize against",
            }
        )
    elif ratio is not None and ratio > 0.20:
        out.append(
            {
                "check": "rework-rate",
                "status": "FLAG",
                "detail": f"rework ratio {ratio:.2f} ({markers}/{denom}) exceeds 0.20",
            }
        )
    else:
        detail = (
            f"rework ratio {ratio:.2f} ({markers}/{denom})"
            if ratio is not None
            else f"{markers} marker(s), denominator 0 (below the 3-marker FLAG floor)"
        )
        out.append({"check": "rework-rate", "status": "PASS", "detail": detail})

    post_n, post_avg, baseline_median = (
        spend["post_n"],
        spend["post_avg"],
        spend["baseline_median"],
    )
    if post_n < 3 or post_avg is None or baseline_median is None:
        out.append(
            {
                "check": "spend-trend",
                "status": "INFO",
                "detail": f"insufficient post-intervention data ({post_n} row(s), need >= 3)",
            }
        )
    elif post_avg > baseline_median:
        out.append(
            {
                "check": "spend-trend",
                "status": "FLAG",
                "detail": f"post_avg ${post_avg:.2f}/day > baseline_median ${baseline_median:.2f}/day "
                f"(interventions not moving the needle yet)",
            }
        )
    else:
        out.append(
            {
                "check": "spend-trend",
                "status": "PASS",
                "detail": f"post_avg ${post_avg:.2f}/day <= baseline_median ${baseline_median:.2f}/day",
            }
        )

    hit_rate = lane["subagent_cache_hit_rate"]
    if hit_rate is None:
        out.append(
            {
                "check": "cache-hit",
                "status": "INFO",
                "detail": "no subagent-lane usage observed in window",
            }
        )
    elif hit_rate < 0.90:
        out.append(
            {
                "check": "cache-hit",
                "status": "FLAG",
                "detail": f"subagent cache-hit rate {hit_rate:.3f} < 0.90 floor (re-measure your own baseline at adoption)",
            }
        )
    else:
        out.append(
            {
                "check": "cache-hit",
                "status": "PASS",
                "detail": f"subagent cache-hit rate {hit_rate:.3f}",
            }
        )

    return out


def build_report(days: int) -> dict:
    spend = spend_trend(load_token_history(TOKEN_HISTORY_PATH))
    files = iter_recent_transcripts(TRANSCRIPT_ROOT, days)
    lane = build_lane_stats(files)
    rework = compute_rework(
        TODO_PATH,
        lane["sonnet_dispatches_subagent"],
        lane["sonnet_calls_subagent"],
    )
    return {
        "intervention_date": INTERVENTION_DATE,
        "days_window": days,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "spend_trend": spend,
        "lane_split": lane,
        "rework": rework,
        "assessment": assess(spend, lane, rework),
    }


def _print_human(report: dict) -> None:
    print(
        f"Tier metrics - intervention {report['intervention_date']}, "
        f"window {report['days_window']}d, generated {report['generated_at']}"
    )

    s = report["spend_trend"]
    print("\nSpend trend:")
    if s["post_avg"] is None:
        print(f"  insufficient data ({s['post_n']} post-intervention row(s))")
    else:
        base = (
            f"${s['baseline_median']:.2f}/day (n={s['baseline_n']})"
            if s["baseline_median"] is not None
            else "n/a"
        )
        print(
            f"  post_avg=${s['post_avg']:.2f}/day (n={s['post_n']})  baseline_median={base}"
        )

    lane = report["lane_split"]
    print("\nLane split:")
    print(f"  files scanned: {lane['files_scanned']}")
    for name in ("main", "subagent"):
        pct = lane["cost_share_pct"].get(name, 0.0)
        print(f"  {name}: ${lane[name]['cost']:.2f} ({pct:.1f}% of window cost)")
    hr = lane["subagent_cache_hit_rate"]
    print(
        f"  subagent cache-hit rate: {hr:.3f}"
        if hr is not None
        else "  subagent cache-hit rate: n/a"
    )
    print("  subagent-lane cost by model family:")
    for fam, pct in sorted(
        lane["subagent_family_share_pct"].items(), key=lambda kv: -kv[1]
    ):
        if pct > 0:
            print(f"    {fam}: {pct:.1f}%")

    rw = report["rework"]
    print("\nRework markers:")
    ratio_str = f"{rw['ratio']:.3f}" if rw["ratio"] is not None else "n/a"
    print(
        f"  SONNET-REWORK markers: {rw['markers']}  sonnet dispatches: {rw['sonnet_dispatches']}"
        f"  (calls: {rw['sonnet_calls']})  ratio: {ratio_str}"
    )

    print("\nAssessment:")
    for a in report["assessment"]:
        print(f"  [{a['status']}] {a['check']}: {a['detail']}")


def selftest() -> int:
    results: list[tuple[str, bool]] = []

    def check(label: str, ok: bool) -> None:
        results.append((label, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    check(
        "sonnet 1M input tokens = $3",
        abs(cost_of_usage({"input_tokens": 1_000_000}, "claude-sonnet-5") - 3.0) < 1e-9,
    )
    check(
        "opus 1M cache_read tokens = $0.50",
        abs(
            cost_of_usage({"cache_read_input_tokens": 1_000_000}, "claude-opus-5") - 0.5
        )
        < 1e-9,
    )
    check(
        "fable 1M output tokens = $50",
        abs(cost_of_usage({"output_tokens": 1_000_000}, "claude-fable-5") - 50.0)
        < 1e-9,
    )
    check(
        "unknown model prices as opus",
        abs(cost_of_usage({"input_tokens": 1_000_000}, "claude-mystery-9") - 5.0)
        < 1e-9,
    )

    check(
        "lane classifier: subagents path",
        classify_lane("C:/x/session/subagents/agent-1.jsonl") == "subagent",
    )
    check(
        "lane classifier: main path",
        classify_lane("C:/x/00057e85-f963-4b72-8c55-a6929d610fd2.jsonl") == "main",
    )

    def lane_fixture(
        sub_cost: float,
        sonnet_cost: float,
        hit_rate: float | None,
        active_days: int = 5,
    ) -> dict:
        return {
            "subagent": {**_zero_bucket(), "cost": sub_cost},
            "subagent_family_cost": {"sonnet": sonnet_cost},
            "subagent_cache_hit_rate": hit_rate,
            "active_days_post": active_days,
        }

    spend_ok = {
        "post_avg": 10.0,
        "baseline_median": 20.0,
        "post_n": 5,
        "baseline_n": 20,
    }

    def rework_status(ratio: float | None, markers: int = 0, disp: int = 10) -> str:
        r = assess(
            spend_ok,
            lane_fixture(100.0, 50.0, 0.95),
            {
                "markers": markers,
                "sonnet_dispatches": disp,
                "sonnet_calls": disp * 40,
                "ratio": ratio,
            },
        )
        return next(a["status"] for a in r if a["check"] == "rework-rate")

    check("rework ratio exactly 0.20 -> PASS", rework_status(0.20, markers=2) == "PASS")
    check(
        "rework ratio 0.21 -> FLAG",
        rework_status(0.21, markers=21, disp=100) == "FLAG",
    )

    def cache_status(hit_rate: float | None) -> str:
        r = assess(
            spend_ok,
            lane_fixture(100.0, 50.0, hit_rate),
            {"markers": 0, "sonnet_dispatches": 0, "sonnet_calls": 0, "ratio": None},
        )
        return next(a["status"] for a in r if a["check"] == "cache-hit")

    check("cache-hit rate exactly 0.90 -> PASS", cache_status(0.90) == "PASS")
    check("cache-hit rate 0.8999 -> FLAG", cache_status(0.8999) == "FLAG")

    check(
        "sonnet-adoption: 0% share, 3 active days -> FLAG",
        next(
            a["status"]
            for a in assess(
                spend_ok,
                lane_fixture(100.0, 0.0, 0.95, active_days=3),
                {
                    "markers": 0,
                    "sonnet_dispatches": 0,
                    "sonnet_calls": 0,
                    "ratio": None,
                },
            )
            if a["check"] == "sonnet-adoption"
        )
        == "FLAG",
    )
    check(
        "sonnet-adoption: nonzero share -> PASS",
        next(
            a["status"]
            for a in assess(
                spend_ok,
                lane_fixture(100.0, 10.0, 0.95, active_days=5),
                {
                    "markers": 0,
                    "sonnet_dispatches": 0,
                    "sonnet_calls": 0,
                    "ratio": None,
                },
            )
            if a["check"] == "sonnet-adoption"
        )
        == "PASS",
    )

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(
        f"\nselftest: {'ALL PASS' if passed == total else 'FAILURES PRESENT'} ({passed}/{total})"
    )
    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    report = build_report(args.days)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
