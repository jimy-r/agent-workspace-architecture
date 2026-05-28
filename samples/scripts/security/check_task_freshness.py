#!/usr/bin/env python3
"""
Dead-man's-switch (R1) — self-hosted alternative to Healthchecks.io.

Scans tasks/scheduled-logs/ for tracked scheduled tasks and reports any whose
most-recent log either does not exist, is older than the configured staleness
window, or does not contain the task's success sentinel.

Based on the watchdog pattern (Pont, *Patterns for Time-Triggered Embedded Systems*,
2002) and Healthchecks.io's "check whether it checked in, not whether it failed"
inversion. See `Reference/Research/2026-05-28_audit-upgrade-best-practices.md`
§4 Gap 1.

Designed to be run daily by Windows Task Scheduler. Stdlib only. Exit code 0
on all-fresh, 1 on any stale, 2 on script error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

WORKSPACE = Path(__file__).resolve().parents[2]
LOGS_DIR = WORKSPACE / "tasks" / "scheduled-logs"
TODO_NOTES = WORKSPACE / "tasks" / "To Do Notes.md"

TRACKED = {
    "morning-brief": {
        "max_age_hours": 30,
        "sentinel": "MORNING_BRIEF_OK",
        "failure_sentinel": "MORNING_BRIEF_FAILED",
        "manual": False,
    },
    "heartbeat-monitor": {
        "max_age_hours": 4,
        "sentinel": "HEARTBEAT_OK",
        "failure_sentinel": "HEARTBEAT_FAILED",
        "manual": False,
    },
    "consolidate-memory": {
        "max_age_hours": 24 * 8,
        "sentinel": "MEMORY_OK",
        "failure_sentinel": "MEMORY_FAILED",
        "manual": False,
    },
    "upgrade-audit": {
        # Manually invoked via scripts/audit.bat. If a log exists and is older
        # than 14 days, surface; if no log exists at all, treat as "MANUAL_OK".
        "max_age_hours": 24 * 14,
        "sentinel": "UPGRADE_AUDIT_OK",
        "failure_sentinel": "UPGRADE_AUDIT_FAILED",
        "manual": True,
    },
}

LOG_PATTERN = re.compile(
    r"^(?P<task>[a-z-]+)_(?P<date>\d{4}-\d{2}-\d{2})-(?P<time>\d{4})\.log$"
)


class Status(NamedTuple):
    task: str
    state: str
    last_run: dt.datetime | None
    age_hours: float | None
    detail: str


def latest_log(task: str) -> Path | None:
    candidates = []
    if not LOGS_DIR.is_dir():
        return None
    for entry in LOGS_DIR.iterdir():
        if not entry.is_file():
            continue
        match = LOG_PATTERN.match(entry.name)
        if not match or match.group("task") != task:
            continue
        candidates.append(entry)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def parse_log_time(log: Path) -> dt.datetime | None:
    match = LOG_PATTERN.match(log.name)
    if not match:
        return None
    date = match.group("date")
    time = match.group("time")
    return dt.datetime.strptime(f"{date}-{time}", "%Y-%m-%d-%H%M")


def check_task(task: str, config: dict) -> Status:
    log = latest_log(task)
    if log is None:
        if config.get("manual"):
            return Status(task, "MANUAL_OK", None, None, "manual task; no log yet")
        return Status(task, "NEVER_RAN", None, None, "no log file matches pattern")

    log_time = parse_log_time(log)
    now = dt.datetime.now()
    age_hours = (now - log_time).total_seconds() / 3600.0 if log_time else None

    try:
        body = log.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return Status(task, "LOG_UNREADABLE", log_time, age_hours, f"read error: {exc}")

    success = config["sentinel"] in body
    failure = config["failure_sentinel"] in body

    if age_hours is not None and age_hours > config["max_age_hours"]:
        return Status(
            task,
            "STALE",
            log_time,
            age_hours,
            f"last log is {age_hours:.1f}h old (max {config['max_age_hours']}h)",
        )

    if failure and not success:
        return Status(
            task,
            "FAILED",
            log_time,
            age_hours,
            "failure sentinel present, no success sentinel",
        )
    if not success:
        return Status(
            task, "NO_SENTINEL", log_time, age_hours, "no success sentinel in last log"
        )
    return Status(task, "FRESH", log_time, age_hours, "ok")


def render_text(statuses: list[Status]) -> str:
    lines = [
        "Task freshness check — " + dt.datetime.now().isoformat(timespec="seconds"),
        "",
    ]
    width = max(len(s.task) for s in statuses)
    for s in statuses:
        age = f"{s.age_hours:6.1f}h" if s.age_hours is not None else "   ----"
        lines.append(f"  {s.task:<{width}}  {s.state:<13}  {age}  {s.detail}")
    return "\n".join(lines) + "\n"


def render_json(statuses: list[Status]) -> str:
    payload = [
        {
            "task": s.task,
            "state": s.state,
            "last_run": s.last_run.isoformat() if s.last_run else None,
            "age_hours": s.age_hours,
            "detail": s.detail,
        }
        for s in statuses
    ]
    return json.dumps(
        {
            "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
            "tasks": payload,
        },
        indent=2,
    )


def append_to_todo_notes(statuses: list[Status]) -> bool:
    """Idempotent: only writes if there's an unresolved stale task and no prior
    same-day entry. Returns True if a write occurred."""
    bad = [s for s in statuses if s.state not in ("FRESH",)]
    if not bad:
        return False
    today = dt.date.today().isoformat()
    marker = f"<!-- dead-mans-switch:{today} -->"
    if not TODO_NOTES.exists():
        return False
    body = TODO_NOTES.read_text(encoding="utf-8")
    if marker in body:
        return False
    lines = [marker, f"### Dead-man's-switch — {today}", ""]
    for s in bad:
        age = f"{s.age_hours:.1f}h" if s.age_hours is not None else "n/a"
        lines.append(
            f"- [DEAD-MAN] `{s.task}` is **{s.state}** (last run {age} ago) — {s.detail}"
        )
    lines.append("")
    insertion = "\n".join(lines)
    section_marker = "## Setup Review"
    if section_marker in body:
        new_body = body.replace(section_marker, insertion + "\n" + section_marker, 1)
    else:
        new_body = body.rstrip() + "\n\n" + insertion + "\n"
    TODO_NOTES.write_text(new_body, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument(
        "--notes", action="store_true", help="append findings to tasks/To Do Notes.md"
    )
    parser.add_argument("--task", help="check only this task")
    args = parser.parse_args()

    tracked = TRACKED
    if args.task:
        if args.task not in TRACKED:
            print(f"unknown task: {args.task}", file=sys.stderr)
            return 2
        tracked = {args.task: TRACKED[args.task]}

    statuses = [check_task(name, cfg) for name, cfg in tracked.items()]

    if args.json:
        print(render_json(statuses))
    else:
        print(render_text(statuses))

    if args.notes:
        if append_to_todo_notes(statuses):
            print("(appended findings to tasks/To Do Notes.md)", file=sys.stderr)

    ok_states = {"FRESH", "MANUAL_OK"}
    return 0 if all(s.state in ok_states for s in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
