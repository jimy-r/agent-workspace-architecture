"""
SessionStart hook — inject the state a session should not have to ask for.

Every session begins by re-establishing the same three facts: what day it
is, what the working tree looks like, and what was left unfinished. Asking
the agent to go and find them costs a handful of tool calls at the most
expensive moment, when nothing is cached yet. A hook that prints them into
the opening context costs one file read.

Anything this hook writes to stdout is added to the session context, so
keep it short. This one caps its task-file excerpt deliberately: a hook
that pastes a 600-line task list into every session has moved the cost
rather than removed it, and it is paid again on every turn.

Adapting it: point `TASK_FILE` at whatever your workspace treats as the
outstanding-work store, and drop the git block if you work outside a repo.

Claude Code hook protocol:
    - stdin: JSON {"hook_event_name": "SessionStart", "source": "startup" |
      "resume" | "clear" | "compact", "cwd": "..."}
    - stdout: added to the session's opening context
    - exit 0: success. A non-zero exit is logged and the session continues

Wired via `.claude/settings.json`; see `samples/.claude/settings.example.json`.
The 2-second timeout there is the point: this must never be something the
operator waits on.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# Relative to the session's working directory.
TASK_FILE = Path("tasks/todo.md")

# How much of the task file to carry in. Past this, point rather than paste.
TASK_LINES = 12

# `resume` and `compact` sessions already carry the prior context, so the
# briefing would be a duplicate. Only fire on a genuinely fresh start.
FRESH_SOURCES = {"startup", "clear"}


def git(cwd: Path, *args: str) -> str | None:
    """Run a read-only git command, or return None outside a repo."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_summary(cwd: Path) -> str | None:
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return None
    status = git(cwd, "status", "--porcelain") or ""
    dirty = len([line for line in status.splitlines() if line.strip()])
    if dirty:
        return f"Branch `{branch}`, {dirty} uncommitted change(s)."
    return f"Branch `{branch}`, working tree clean."


def task_excerpt(cwd: Path) -> str | None:
    path = cwd / TASK_FILE
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    kept = [line for line in lines if line.strip()][:TASK_LINES]
    if not kept:
        return None
    body = "\n".join(kept)
    more = (
        ""
        if len(lines) <= TASK_LINES
        else f"\n(… read {TASK_FILE.as_posix()} for the rest.)"
    )
    return f"Top of {TASK_FILE.as_posix()}:\n{body}{more}"


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}

    if payload.get("source") not in FRESH_SOURCES:
        return 0

    cwd = Path(payload.get("cwd") or ".")

    parts = [f"Session opened {dt.datetime.now().astimezone().date().isoformat()}."]
    summary = git_summary(cwd)
    if summary:
        parts.append(summary)
    excerpt = task_excerpt(cwd)
    if excerpt:
        parts.append(excerpt)

    print("\n\n".join(parts))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — intentional fail-open
        # A briefing is a nicety. It never gets to hold up a session start.
        print(f"[session-start] hook error (failing open): {exc}", file=sys.stderr)
        sys.exit(0)
