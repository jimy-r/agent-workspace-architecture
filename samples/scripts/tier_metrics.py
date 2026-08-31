#!/usr/bin/env python3
# Redacted sample from the private workspace - see PATTERNS.md Pattern 15
# ("Price the lane before you migrate it"). Measures a token-management
# intervention set: lane split, cache-hit, model adoption, rework markers,
# cost per accepted dispatch, spend-tail concentration.
# Adapt TRANSCRIPT_ROOT, INTERVENTION_DATE, and the FLAG thresholds to yours.
"""Read-only measurement instrument for the 2026-08-13 token-management
interventions (ultracode default off, differentiated effort map, Fable to
Sonnet execution trial).

INTERVENTION_DATE marks the day those interventions landed: rows/transcript
activity on or after it are "post", the 28 days before it are "baseline".

Computes six things:
  1. Spend trend      - token_history.jsonl daily $ before/after the date.
  2. Lane split        - main vs subagent-lane transcript cost share, the
                          subagent lane's cache-hit rate, and Sonnet-adoption
                          share (cost by model family) within that lane.
  3. Rework markers     - "SONNET-REWORK" occurrences in tasks/todo.md against
                          subagent-lane Sonnet DISPATCHES (one transcript file
                          = one task; the 20% kill criterion is per task).
  4. Cost per task      - dispatch_ledger.jsonl verdicts joined with the
                          lane's per-family cost: $ per ACCEPTED dispatch by
                          tier. A tier trial is ruled on cost per accepted
                          task, not cost per token.
  5. Spend tail          - share of subagent-lane cost carried by the top
                          decile of transcript files. A concentrated tail is
                          where tiering/effort levers pay.
  6. Assessment          - PASS / FLAG / INFO verdicts on the checks above
                          (sonnet-adoption, rework-rate, spend-trend,
                          cache-hit, cost-per-task, spend-tail). Advisory
                          only: never exits non-zero for a FLAG, only for a
                          --selftest failure or a crash.

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
# Event log written by a per-dispatch router (route + outcome rows per id);
# absent file = the cost-per-task section degrades to INFO, nothing fails.
LEDGER_PATH = WORKSPACE / "scripts" / "_state" / "dispatch_ledger.jsonl"
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
    subagent_file_costs: list[float] = []

    for path in files:
        lane = classify_lane(str(path))
        file_has_sonnet = False
        file_cost = 0.0
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
                    file_cost += cost
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
        if lane == "subagent":
            subagent_file_costs.append(file_cost)
            if file_has_sonnet:
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
        "subagent_file_costs": subagent_file_costs,
    }


def load_dispatch_states(path: Path, since_date: str) -> dict:
    """Reduce the route/outcome event log to latest-state-per-id.

    dispatch_ledger.jsonl is an EVENT LOG (route + outcome rows share an id) -
    never row-count it. Keeps dispatches whose route ts date >= since_date.
    """
    states: dict[str, dict] = {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                id_ = obj.get("id")
                if not isinstance(id_, str) or not id_:
                    continue
                event = obj.get("event")
                if event == "route":
                    s = states.setdefault(id_, {})
                    s["tier"] = obj.get("tier")
                    s["ts"] = obj.get("ts") or ""
                elif event == "outcome":
                    states.setdefault(id_, {})["verdict"] = obj.get("verdict")
    except OSError:
        return {}
    return {
        i: s
        for i, s in states.items()
        if isinstance(s.get("ts"), str) and s["ts"][:10] >= since_date
    }


def cost_per_task(lane: dict, states: dict) -> dict:
    """Average subagent-lane cost per ledger-ACCEPTED dispatch, by tier.

    Family cost is the whole window's transcript cost for that model family;
    ledger dispatches are the router-consulted subset. So the figure is an
    average over the lane, not a per-task join - labeled as such in output.
    """
    by_tier: dict[str, dict] = {}
    for s in states.values():
        tier = s.get("tier") or "unknown"
        b = by_tier.setdefault(
            tier,
            {
                "dispatches": 0,
                "accepted": 0,
                "rework": 0,
                "escalated": 0,
                "no_outcome": 0,
            },
        )
        b["dispatches"] += 1
        v = s.get("verdict")
        if v in ("accepted", "rework", "escalated"):
            b[v] += 1
        else:
            b["no_outcome"] += 1
    for tier, b in by_tier.items():
        fam_cost = lane["subagent_family_cost"].get(tier)
        b["family_cost"] = fam_cost
        b["cost_per_accepted"] = (
            fam_cost / b["accepted"]
            if isinstance(fam_cost, (int, float)) and fam_cost > 0 and b["accepted"] > 0
            else None
        )
    return by_tier


def tail_concentration(file_costs: list[float]) -> dict | None:
    """Share of subagent-lane cost carried by the top decile of transcript
    files. Anthropic's production observation: the hardest 10% of tasks carry
    ~43% of spend - the tail is where tiering/effort levers pay."""
    if len(file_costs) < 10:
        return None
    xs = sorted(file_costs, reverse=True)
    k = max(1, len(xs) // 10)
    total = sum(xs)
    if total <= 0:
        return None
    return {
        "files": len(xs),
        "top_decile_files": k,
        "top_decile_share": sum(xs[:k]) / total,
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


def assess(
    spend: dict,
    lane: dict,
    rework: dict,
    cpt: dict | None = None,
    tail: dict | None = None,
) -> list[dict]:
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

    # Advisory INFO only: a tier trial is ruled on cost per ACCEPTED task,
    # not per token. No FLAG threshold until your own baseline exists.
    if cpt:
        parts = []
        for tier, b in sorted(cpt.items()):
            if b.get("cost_per_accepted") is not None:
                parts.append(
                    f"{tier} ${b['cost_per_accepted']:.2f}/accepted "
                    f"({b['accepted']}/{b['dispatches']} accepted)"
                )
        if parts:
            out.append(
                {
                    "check": "cost-per-task",
                    "status": "INFO",
                    "detail": "; ".join(parts),
                }
            )

    if tail:
        out.append(
            {
                "check": "spend-tail",
                "status": "INFO",
                "detail": (
                    f"top decile ({tail['top_decile_files']} of {tail['files']} "
                    f"subagent files) carries {tail['top_decile_share']:.0%} of "
                    "lane cost"
                ),
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
    cpt = cost_per_task(lane, load_dispatch_states(LEDGER_PATH, INTERVENTION_DATE))
    tail = tail_concentration(lane["subagent_file_costs"])
    return {
        "intervention_date": INTERVENTION_DATE,
        "days_window": days,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "spend_trend": spend,
        "lane_split": lane,
        "rework": rework,
        "cost_per_task": cpt,
        "tail_concentration": tail,
        "assessment": assess(spend, lane, rework, cpt, tail),
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

    cpt = report.get("cost_per_task") or {}
    if cpt:
        print("\nCost per accepted dispatch (lane average, by tier):")
        for tier, b in sorted(cpt.items()):
            cpa = (
                f"${b['cost_per_accepted']:.2f}/accepted"
                if b.get("cost_per_accepted") is not None
                else "n/a"
            )
            print(
                f"  {tier}: {cpa}  ({b['accepted']} accepted / {b['rework']} rework /"
                f" {b['escalated']} escalated / {b['no_outcome']} no-outcome"
                f" of {b['dispatches']} dispatches)"
            )

    tail = report.get("tail_concentration")
    if tail:
        print(
            f"\nSpend tail: top {tail['top_decile_files']} of {tail['files']} subagent"
            f" files carry {tail['top_decile_share']:.0%} of lane cost"
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

    # Cost per task: event-log reduce (route+outcome share an id) + the join.
    import tempfile

    ledger_rows = [
        {"ts": "2026-08-20T10:00:00", "event": "route", "id": "a1", "tier": "sonnet"},
        {"event": "outcome", "id": "a1", "verdict": "accepted"},
        {"ts": "2026-08-21T10:00:00", "event": "route", "id": "a2", "tier": "sonnet"},
        {"event": "outcome", "id": "a2", "verdict": "rework"},
        {"ts": "2026-08-22T10:00:00", "event": "route", "id": "a3", "tier": "opus"},
        {"ts": "2026-08-01T10:00:00", "event": "route", "id": "old", "tier": "opus"},
    ]
    with tempfile.TemporaryDirectory() as td:
        lp = Path(td) / "ledger.jsonl"
        lp.write_text("\n".join(json.dumps(r) for r in ledger_rows), encoding="utf-8")
        states = load_dispatch_states(lp, "2026-08-13")
        check(
            "ledger reduce: 3 in-window dispatches, old row dropped", len(states) == 3
        )
        cpt = cost_per_task(lane_fixture(100.0, 50.0, 0.95), states)
        check(
            "cost_per_accepted: sonnet $50 family cost / 1 accepted = $50",
            abs((cpt["sonnet"]["cost_per_accepted"] or 0) - 50.0) < 1e-9,
        )
        check(
            "cost_per_accepted: opus no accepted -> None",
            cpt["opus"]["cost_per_accepted"] is None and cpt["opus"]["no_outcome"] == 1,
        )
    check(
        "load_dispatch_states: absent file -> {}",
        load_dispatch_states(Path("does/not/exist.jsonl"), "2026-08-13") == {},
    )

    tail = tail_concentration([100.0] + [1.0] * 19)
    check(
        "tail: 2 of 20 files, dominant file concentrates the share",
        tail is not None
        and tail["top_decile_files"] == 2
        and tail["top_decile_share"] > 0.8,
    )
    check("tail: under 10 files -> None", tail_concentration([1.0] * 9) is None)

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
