#!/usr/bin/env python3
"""Coded audit assertions (checks-as-code, 2026-06-10).

The weekly audit historically performed its Phase 0 / 2.9 / universal checks
as natural-language instructions re-interpreted by the agent each run -which
produced a false positive on 2026-06-04 (a "missing" heartbeat budget flag
that had existed since 2026-05-29). Per the workspace lesson "unattended
steps must be deterministic code, not LLM reasoning", the assertions live
here as code. The audit agent runs this file and REASONS OVER THE RESULTS;
it does not re-derive them.

Each check returns PASS / WARN / FAIL plus evidence (file + the observed
value). Exit code: 0 if no FAIL (WARNs allowed), 1 otherwise.

Usage:
  python scripts/audit_checks/run_all.py [--json] [--group G1|G2|G3|G4|universal|all]

Note on canaries: the `canary_fixtures` check verifies fixture INTEGRITY only
(the trigger strings are still present in tests/audit_canaries/). DETECTION
is asserted by the audit itself at end-of-run: each canary's expected finding
must actually appear in the corresponding phase's output. A canary with an
intact fixture but no surfaced finding means the detector regressed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def _result(name: str, group: str, status: str, evidence: str) -> dict:
    return {"check": name, "group": group, "status": status, "evidence": evidence}


def check_canary_fixtures() -> dict:
    manifest = WORKSPACE / "tests" / "audit_canaries" / "canary.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _result("canary_fixtures", "G1", "FAIL", f"manifest unreadable: {exc}")
    missing = []
    for canary in data.get("canaries", []):
        path = WORKSPACE / canary["path"]
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing.append(f"{canary['id']}: file missing ({canary['path']})")
            continue
        if canary["expected_pattern"] not in body:
            missing.append(f"{canary['id']}: pattern absent from {canary['path']}")
    if missing:
        return _result("canary_fixtures", "G1", "FAIL", "; ".join(missing))
    n = len(data.get("canaries", []))
    return _result(
        "canary_fixtures",
        "G1",
        "PASS",
        f"{n} fixtures intact (integrity only - detection asserted end-of-run)",
    )


def check_public_mirror_drift() -> dict:
    private = WORKSPACE / "META_ARCHITECTURE.md"
    public = WORKSPACE / "agent-workspace-architecture" / "META_ARCHITECTURE.md"
    date_re = re.compile(r"Last updated:\*{0,2}\s*(\d{4}-\d{2}-\d{2})")
    try:
        priv_text = private.read_text(encoding="utf-8", errors="replace")
        pub_text = public.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _result("public_mirror_drift", "G1", "WARN", f"unreadable: {exc}")
    priv_date = date_re.search(priv_text)
    pub_date = date_re.search(pub_text)
    if not (priv_date and pub_date):
        return _result(
            "public_mirror_drift",
            "G1",
            "WARN",
            "Last-updated line not found in one side",
        )
    d_priv = dt.date.fromisoformat(priv_date.group(1))
    d_pub = dt.date.fromisoformat(pub_date.group(1))
    gap = (d_priv - d_pub).days
    sec_re = re.compile(r"^## \d+\.", re.MULTILINE)
    priv_sections = len(sec_re.findall(priv_text))
    pub_sections = len(sec_re.findall(pub_text))
    if gap > 14:
        return _result(
            "public_mirror_drift",
            "G1",
            "FAIL",
            f"public {gap}d behind ({d_pub} vs {d_priv})",
        )
    if priv_sections > pub_sections:
        return _result(
            "public_mirror_drift",
            "G1",
            "FAIL",
            f"private has {priv_sections} numbered sections vs public {pub_sections}",
        )
    return _result(
        "public_mirror_drift",
        "G1",
        "PASS",
        f"dates {d_pub}/{d_priv} (gap {gap}d); numbered sections {priv_sections}/{pub_sections}",
    )


def _latest_log_age_hours(prefix: str) -> float | None:
    logs_dir = WORKSPACE / "tasks" / "scheduled-logs"
    pattern = re.compile(
        rf"^{re.escape(prefix)}_(\d{{4}}-\d{{2}}-\d{{2}})-(\d{{4}})\.log$"
    )
    newest = None
    if logs_dir.is_dir():
        for entry in logs_dir.iterdir():
            m = pattern.match(entry.name)
            if m:
                stamp = dt.datetime.strptime(
                    f"{m.group(1)}-{m.group(2)}", "%Y-%m-%d-%H%M"
                )
                if newest is None or stamp > newest:
                    newest = stamp
    if newest is None:
        return None
    return (dt.datetime.now() - newest).total_seconds() / 3600.0


def check_backup_recency() -> dict:
    age = _latest_log_age_hours("backup-restic")
    if age is None:
        return _result("backup_recency", "G1", "WARN", "no backup-restic log found")
    days = age / 24.0
    if days > 30:
        return _result(
            "backup_recency", "G1", "FAIL", f"last backup {days:.1f}d ago (>30d)"
        )
    if days > 7:
        return _result(
            "backup_recency",
            "G1",
            "WARN",
            f"last backup {days:.1f}d ago (>7d nudge threshold)",
        )
    return _result("backup_recency", "G1", "PASS", f"last backup {days:.1f}d ago")


def check_rotation_state() -> dict:
    path = WORKSPACE / "scripts" / "_state" / "audit_module_rotation.txt"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return _result("rotation_state", "G1", "FAIL", f"unreadable: {exc}")
    if value not in {"G1", "G2", "G3", "G4"}:
        return _result("rotation_state", "G1", "FAIL", f"invalid value {value!r}")
    return _result("rotation_state", "G1", "PASS", f"active group {value}")


def check_heartbeat_budget() -> dict:
    wrapper = WORKSPACE / "scripts" / "run-scheduled-skill.ps1"
    try:
        body = wrapper.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _result("heartbeat_budget", "G2", "FAIL", f"wrapper unreadable: {exc}")
    if "--max-budget-usd" not in body:
        return _result(
            "heartbeat_budget",
            "G2",
            "FAIL",
            "--max-budget-usd absent from run-scheduled-skill.ps1",
        )
    return _result(
        "heartbeat_budget",
        "G2",
        "PASS",
        "--max-budget-usd present in run-scheduled-skill.ps1",
    )


def check_heartbeat_model_map() -> dict:
    wrapper = WORKSPACE / "scripts" / "run-scheduled-skill.ps1"
    try:
        body = wrapper.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _result(
            "heartbeat_model_map", "G2", "FAIL", f"wrapper unreadable: {exc}"
        )
    if "ModelMap" not in body or "heartbeat-monitor" not in body:
        return _result(
            "heartbeat_model_map",
            "G2",
            "FAIL",
            "scheduled-task model map missing from wrapper",
        )
    return _result(
        "heartbeat_model_map",
        "G2",
        "PASS",
        "model map present (scheduled tasks re-tiered)",
    )


def check_heartbeat_gate() -> dict:
    gate = WORKSPACE / "scripts" / "heartbeat" / "preflight_gate.py"
    state = WORKSPACE / "scripts" / "_state" / "heartbeat_gate.json"
    if not gate.exists():
        return _result("heartbeat_gate", "G2", "FAIL", "preflight_gate.py missing")
    if not state.exists():
        return _result(
            "heartbeat_gate",
            "G2",
            "WARN",
            "gate present but no state yet (no gated cycle has run)",
        )
    age_h = (
        dt.datetime.now() - dt.datetime.fromtimestamp(state.stat().st_mtime)
    ).total_seconds() / 3600
    return _result(
        "heartbeat_gate", "G2", "PASS", f"gate + state present (state {age_h:.1f}h old)"
    )


def check_health_staleness() -> dict:
    path = WORKSPACE / "scripts" / "_state" / "health_history.jsonl"
    if not path.exists():
        return _result(
            "health_staleness",
            "universal",
            "WARN",
            "health skill has never run (no health_history.jsonl) - run /health or retire the skill",
        )
    days = (dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)).days
    if days > 30:
        return _result(
            "health_staleness", "universal", "WARN", f"last /health run {days}d ago"
        )
    return _result(
        "health_staleness", "universal", "PASS", f"last /health run {days}d ago"
    )


def check_token_history() -> dict:
    path = WORKSPACE / "scripts" / "_state" / "token_history.jsonl"
    if not path.exists():
        return _result(
            "token_history",
            "universal",
            "WARN",
            "token_history.jsonl missing - morning brief should be running token_report.py log",
        )
    days = (dt.datetime.now() - dt.datetime.fromtimestamp(path.stat().st_mtime)).days
    if days > 8:
        return _result(
            "token_history",
            "universal",
            "WARN",
            f"token history last updated {days}d ago",
        )
    return _result(
        "token_history", "universal", "PASS", f"token history current ({days}d old)"
    )


CHECKS = [
    check_canary_fixtures,
    check_public_mirror_drift,
    check_backup_recency,
    check_rotation_state,
    check_heartbeat_budget,
    check_heartbeat_model_map,
    check_heartbeat_gate,
    check_health_staleness,
    check_token_history,
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--group", default="all", help="G1|G2|G3|G4|universal|all")
    args = parser.parse_args()

    results = [fn() for fn in CHECKS]
    if args.group != "all":
        results = [r for r in results if r["group"] in (args.group, "universal")]

    if args.json:
        print(
            json.dumps(
                {
                    "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "results": results,
                },
                indent=2,
            )
        )
    else:
        width = max(len(r["check"]) for r in results)
        for r in results:
            print(
                f"  {r['check']:<{width}}  {r['status']:<5}  [{r['group']}]  {r['evidence']}"
            )

    return 0 if all(r["status"] != "FAIL" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
