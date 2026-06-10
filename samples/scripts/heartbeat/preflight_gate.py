#!/usr/bin/env python3
"""Stage-0 gate for the heartbeat scheduled task (gate-don't-loop, 2026-06-10).

Run by run-scheduled-skill.ps1 BEFORE invoking claude for heartbeat-monitor.
Decides whether this 2-hourly fire needs the LLM at all:

  SKIP (exit 100) when ALL of:
    - the watched task files are unchanged since the last agent cycle
    - the deterministic preflight scans pass (roles validator, memory lint)
    - the last full agent cycle is younger than the daily floor (24h)
  The wrapper then logs "HEARTBEAT_OK (gated skip)" and exits without
  invoking claude. Most of the 12 daily fires should end here.

  RUN (exit 0) otherwise. Stdout carries a PREFLIGHT block the wrapper
  appends to the SKILL prompt so the agent does not re-run the scans.

  Any other exit code = gate bug. The wrapper FAILS OPEN and runs the
  agent -a broken gate must never silence the heartbeat.

State: scripts/_state/heartbeat_gate.json
  {"hash": "<sha256 of watched inputs>", "last_agent_cycle": "<iso>"}
The stored hash is refreshed by `--mark-cycle` AFTER a successful agent
cycle, not at gate time -the agent itself edits the watched files
mid-cycle (posting questions, striking bullets), so hashing at gate time
would re-trigger a RUN on every subsequent fire.

Context: from 2026-06-15 headless `claude -p` draws from a capped monthly
credit pool; this gate is the workspace's main lever for fitting inside it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
STATE_FILE = WORKSPACE / "scripts" / "_state" / "heartbeat_gate.json"

WATCHED = [
    WORKSPACE / "tasks" / "To Do Notes.md",
    WORKSPACE / "tasks" / "To Do Questions.md",
    WORKSPACE / "tasks" / "HEARTBEAT_REVIEWS.md",
    WORKSPACE / "tasks" / "HEARTBEAT_REJECTIONS.md",
]
DRY_RUN_MARKER = WORKSPACE / "tasks" / ".heartbeat-dry-run"

AGENT_FLOOR_HOURS = 24  # run the full agent at least daily even when quiet
SCAN_TIMEOUT_S = 120

SCANS = [
    ("roles-validator", [sys.executable, str(WORKSPACE / "roles" / "_validate.py")]),
    ("memory-lint", [sys.executable, str(WORKSPACE / "scripts" / "memory_lint.py")]),
]

EXIT_RUN = 0
EXIT_SKIP = 100


def watched_hash() -> str:
    h = hashlib.sha256()
    for path in WATCHED:
        h.update(path.name.encode("utf-8"))
        if path.exists():
            h.update(path.read_bytes())
        else:
            h.update(b"<missing>")
    h.update(b"dry-run:" + (b"present" if DRY_RUN_MARKER.exists() else b"absent"))
    return h.hexdigest()


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_scans() -> list[tuple[str, bool, str]]:
    results = []
    for name, cmd in SCANS:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SCAN_TIMEOUT_S,
                cwd=str(WORKSPACE),
            )
            passed = proc.returncode == 0
            tail = (proc.stdout + proc.stderr).strip().splitlines()
            detail = tail[-1][:160] if tail else f"exit {proc.returncode}"
        except Exception as exc:  # scan crash counts as a failure -> RUN
            passed, detail = False, f"scan error: {exc}"[:160]
        results.append((name, passed, detail))
    return results


def cycle_age_hours(state: dict) -> float | None:
    raw = state.get("last_agent_cycle")
    if not raw:
        return None
    try:
        then = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    return (dt.datetime.now() - then).total_seconds() / 3600.0


def mark_cycle() -> int:
    state = load_state()
    state["hash"] = watched_hash()
    state["last_agent_cycle"] = dt.datetime.now().isoformat(timespec="seconds")
    save_state(state)
    print(
        f"gate state stamped: cycle at {state['last_agent_cycle']}, hash ...{state['hash'][-8:]}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mark-cycle",
        action="store_true",
        help="stamp a completed agent cycle (wrapper calls this after the HEARTBEAT_OK sentinel)",
    )
    args = parser.parse_args()

    if args.mark_cycle:
        return mark_cycle()

    now = dt.datetime.now().isoformat(timespec="seconds")
    state = load_state()
    current = watched_hash()
    changed = state.get("hash") != current
    scans = run_scans()
    failed = [name for name, passed, _ in scans if not passed]
    age = cycle_age_hours(state)
    overdue = age is None or age >= AGENT_FLOOR_HOURS

    reasons = []
    if changed:
        reasons.append("watched task files changed")
    for name in failed:
        reasons.append(f"scan failed: {name}")
    if overdue:
        reasons.append(
            "daily floor (no agent cycle yet)"
            if age is None
            else f"daily floor ({age:.1f}h since last agent cycle)"
        )

    decision = "RUN" if reasons else "SKIP"

    lines = [f"PREFLIGHT (preflight_gate.py @ {now}):"]
    lines.append(
        f"- watched inputs: {'CHANGED' if changed else 'unchanged'} (sha256 ...{current[-8:]})"
    )
    for name, passed, detail in scans:
        lines.append(f"- {name}: {'PASS' if passed else 'FAIL'} - {detail}")
    lines.append(
        f"- last agent cycle: {'never recorded' if age is None else f'{age:.1f}h ago'}"
    )
    lines.append(
        f"- dry-run marker: {'present' if DRY_RUN_MARKER.exists() else 'absent'}"
    )
    lines.append(
        f"- decision: {decision}" + (f" ({'; '.join(reasons)})" if reasons else "")
    )
    if decision == "RUN":
        lines.append(
            "Agent: the scans above already ran this cycle - do NOT re-run the roles validator "
            "or memory lint; report their preflight results in the HB_STATUS scans= field."
        )
    print("\n".join(lines))

    return EXIT_RUN if decision == "RUN" else EXIT_SKIP


if __name__ == "__main__":
    sys.exit(main())
