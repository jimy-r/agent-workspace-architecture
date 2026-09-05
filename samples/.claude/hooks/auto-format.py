"""
PostToolUse Edit/Write hook — format the file the agent just touched.

Formatting drift is the cheapest kind of review noise: a diff where half
the changed lines are whitespace hides the two lines that matter. Running
the formatter at the moment of the edit keeps the diff honest, and keeps
the agent from spending a turn on it later.

Deliberately conservative. If the formatter for a file type is not on
PATH, the hook says so and exits 0 rather than failing the session, so
this file can be dropped into any workspace without first installing a
toolchain. It also never touches a file the agent did not just edit.

Adapting it: edit `FORMATTERS` below. Key is the file suffix, value is
the command to run with the file path appended. Anything absent from the
table is left alone.

Claude Code hook protocol:
    - stdin: JSON {"tool_name": "Edit", "tool_input": {"file_path": "..."},
      "tool_response": {...}}
    - exit 0: success. Anything printed to stdout is shown to the operator
      in transcript mode but is not fed back to the agent
    - exit 2: stderr is fed back to the agent. This hook never does that —
      a formatter failure is not the agent's problem to solve

Wired via `.claude/settings.json`; see `samples/.claude/settings.example.json`.
The 30-second timeout there is sized for a cold formatter start on a large
file; the steady-state cost is tens of milliseconds.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

# suffix → command. The edited file's path is appended as the last argument.
FORMATTERS: dict[str, list[str]] = {
    ".py": ["ruff", "format"],
    ".md": ["prettier", "--write"],
    ".json": ["prettier", "--write"],
    ".yml": ["prettier", "--write"],
    ".yaml": ["prettier", "--write"],
    ".js": ["prettier", "--write"],
    ".ts": ["prettier", "--write"],
    ".css": ["prettier", "--write"],
    ".html": ["prettier", "--write"],
}

WATCHED_TOOLS = {"Edit", "Write", "MultiEdit"}

# A formatter that has not finished in this long is stuck, not slow. Stay
# well under the hook timeout in settings.json so the failure is ours to
# report rather than an opaque kill.
TIMEOUT_SECONDS = 20


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    payload = json.loads(raw)
    if payload.get("tool_name") not in WATCHED_TOOLS:
        return 0

    target = (payload.get("tool_input") or {}).get("file_path") or ""
    if not target:
        return 0

    path = Path(target)
    if not path.is_file():
        # The edit failed, or the path is a notebook cell reference.
        return 0

    command = FORMATTERS.get(path.suffix.lower())
    if command is None:
        return 0

    if shutil.which(command[0]) is None:
        print(f"[auto-format] {command[0]} not on PATH; skipping {path.name}.")
        return 0

    try:
        result = subprocess.run(
            [*command, str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(f"[auto-format] {command[0]} timed out on {path.name}.", file=sys.stderr)
        return 0

    if result.returncode != 0:
        # A syntax error in the file the agent is midway through writing is
        # the common case, and it resolves itself on the next edit. Report
        # it and get out of the way.
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        first = detail[0] if detail else f"exit {result.returncode}"
        print(f"[auto-format] {command[0]} failed on {path.name}: {first}")
        return 0

    print(f"[auto-format] {command[0]} formatted {path.name}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — intentional fail-open
        # Formatting is a convenience. It never gets to break the session.
        print(f"[auto-format] hook error (failing open): {exc}", file=sys.stderr)
        sys.exit(0)
