"""
PreToolUse Edit/Write hook — refuse edits to sensitive files.

The cheapest insurance in the whole system, and the one ADOPTION.md's
step 3 asks you to write first. An agent that has gone sideways will
happily rewrite your `.env` or truncate a financial workbook; a hook
that costs ten milliseconds stops the overwhelming majority of that
class of accident before the tool call runs.

Scope: `Edit` and `Write` only. Shell-level writes (`>`, `sed -i`, `mv`)
go through the `Bash` tool and bypass this hook entirely — that gap is
what `scripts/security/check_bash_command.py` closes. Wire both.

This is defence-in-depth, not a security boundary. The bar is "catch
casual mistakes", not "stop a determined adversary": a process that
opens a file internally (`open(path, "w")` inside a script the agent
runs) is out of reach of any PreToolUse hook.

Adapting it: edit `BLOCKED` below. Entries are matched against the
target path in three ways — a bare filename glob (`.env*`), a path
fragment (`finance/`), or a suffix (`.pem`). Keep the list
short enough that you can read it, and put anything you would not want
to restore from backup on it.

Claude Code hook protocol:
    - stdin: JSON {"tool_name": "Edit", "tool_input": {"file_path": "..."}}
    - exit 0: allow the tool call
    - exit 2: block it; stderr is surfaced to the agent. The structured
      form is JSON on stdout: {"decision": "block", "reason": "..."}
    - any other exit code: treated as a non-blocking error

Wired via `.claude/settings.json`; see `samples/.claude/settings.example.json`.
"""

from __future__ import annotations

import fnmatch
import json
import sys

# Path shapes this hook refuses to let Edit/Write touch.
#
#   *pattern*  → filename glob, matched against the basename
#   ends with / → path fragment, matched anywhere in the path
#   otherwise  → matched as a filename glob AND as a path fragment
#
# Matching is case-insensitive and runs on forward-slash-normalised paths,
# so the same list works on Windows and POSIX.
BLOCKED: tuple[str, ...] = (
    # Credentials and keys. Nothing here should be in a repo at all, which
    # is exactly why an agent editing one means something has gone wrong.
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "id_rsa*",
    "credentials*",
    "secrets*",
    ".npmrc",
    ".pypirc",
    # Data you cannot reconstruct from a diff. Localise these to your own
    # tree: the point is the shape, not these particular folder names.
    "finance/",
    "medical-records/",
    ".git/config",
)

# Tools whose input carries a target file path.
WATCHED_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def normalise(path: str) -> str:
    """Lower-case, forward-slash form so one pattern list covers every OS."""
    return path.replace("\\", "/").lower()


def match_reason(path: str) -> str | None:
    """Return the pattern that blocks this path, or None if it is allowed."""
    if not path:
        return None
    norm = normalise(path)
    basename = norm.rsplit("/", 1)[-1]

    for pattern in BLOCKED:
        pat = normalise(pattern)
        if pat.endswith("/"):
            if pat in norm:
                return pattern
            continue
        if fnmatch.fnmatch(basename, pat):
            return pattern
        if pat in norm:
            return pattern
    return None


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    payload = json.loads(raw)
    if payload.get("tool_name") not in WATCHED_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""

    pattern = match_reason(target)
    if pattern is None:
        return 0

    reason = (
        f"Refusing to edit {target!r}: it matches the protected pattern "
        f"{pattern!r} in the PreToolUse file-protection hook. If this edit is "
        f"genuinely intended, the operator has to make it by hand."
    )
    print(json.dumps({"decision": "block", "reason": f"[protect-files] {reason}"}))
    print(f"[protect-files] BLOCKED: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — intentional fail-open
        # A buggy hook must never brick every Edit and Write in the session.
        # Failing open is the deliberate trade: this is a mistake-catcher,
        # and a mistake-catcher that blocks all work gets deleted on day one.
        print(f"[protect-files] hook error (failing open): {exc}", file=sys.stderr)
        sys.exit(0)
