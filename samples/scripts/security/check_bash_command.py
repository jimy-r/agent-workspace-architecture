"""
PreToolUse Bash hook — close the Bash gap in Edit/Write file protection
and block dangerous git operations.

Background: the existing PreToolUse hook at `~/.claude/settings.json`
gates `Edit` and `Write` tool calls against a list of protected path
substrings. But shell-level filesystem operations (`mv`, `cp`, `sed -i`,
`rm`, output redirection `>` / `>>`) bypass that hook because they go
through the `Bash` tool, not `Edit`/`Write`. Discovered during the
heartbeat-as-PR-agent cutover on 2026-04-22 (see `tasks/lessons.md`).

This hook wires in as a PreToolUse matcher on `Bash` and refuses two
categories of command:

    1. File writes to protected paths — any write-intent verb (`>` /
       `>>` / `2>` / `rm` / `mv <dest>` / `cp <dest>` / `sed -i` /
       `tee` / `touch` / `chmod` / `chown`) whose target contains a
       protected path substring (case-insensitive, normalised to
       forward slashes).

    2. Dangerous git operations — `git push` targeting `main` or
       `master`, any force push, `git reset --hard` against main/master.

This is *defence-in-depth*, not paranoia. The bar is "catch casual
mistakes," not "stop a determined adversary." Python and Node processes
that open files internally (`open(path, 'w')`) are out of scope — the
hook can't inspect process behaviour.

Claude Code hook protocol:
    - stdin: JSON payload {"tool_name": "Bash", "tool_input": {"command": "..."}}
    - exit 0: allow
    - exit 2: block (stderr message is surfaced to the agent; JSON on
      stdout with {"decision": "block", "reason": "..."} is the
      structured form)

If the hook script itself errors, it fails open (exit 0, no block) so
a bug here does NOT brick the agent's ability to run Bash.
"""

from __future__ import annotations

import json
import re
import sys

# ---------------------------------------------------------------------------
# Protected-path substrings (case-insensitive, match after normalising
# backslashes to forward slashes in the target).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Allowlist — path substrings where protected filenames are intentional
# copies (sample/mirror files, not the live protected file). If a target
# contains any ALLOWLIST substring, the protection check is skipped.
# ---------------------------------------------------------------------------

ALLOWLIST_SUBSTRINGS: list[str] = [
    "agent-workspace-architecture/samples/",
    # Add further sample/mirror roots here if more public repos get cloned in.
]


PROTECTED_SUBSTRINGS: list[str] = [
    # Credentials / secrets
    ".env",
    "credentials",
    "secrets",
    ".key",
    ".pem",
    # Lock files the agent shouldn't hand-edit
    "renv.lock",
    # Heartbeat agent's own files
    "heartbeat.md",
    "heartbeat_rejections.md",  # append-only log — never edit existing blocks
    # Health data
    "health_profile.md",
    "personal/health/pathology",
    "personal/health/medication",
    "personal/health/immunisations",
    "personal/health/nutrition",
    "personal/health/general",
    "personal/health/sleep",
    "personal/health/documents to process",
    # Financial data
    "personal/accounts/results",
    "personal/accounts/records",
    # Google OAuth
    "/.claude/google-auth/",
    "google-auth/",
]

# ---------------------------------------------------------------------------
# Write-intent patterns. Each captures the target path as group(2).
# The path token is terminated by whitespace, pipe, semicolon, ampersand,
# or end of string. Single and double quotes optionally wrap the target.
# ---------------------------------------------------------------------------

_PATH = r"(['\"]?)([^\s'\"|&;<>]+)\1"

WRITE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?<![2&])>\s*{_PATH}"), "shell redirection '>'"),
    (re.compile(rf">>\s*{_PATH}"), "shell append '>>'"),
    (re.compile(rf"2>\s*{_PATH}"), "stderr redirection '2>'"),
    (re.compile(rf"\brm\s+(?:-[rRfv]+\s+)*{_PATH}"), "rm"),
    (re.compile(rf"\bmv\s+\S+\s+{_PATH}"), "mv (destination)"),
    (re.compile(rf"\bcp\s+(?:-\S+\s+)*\S+\s+{_PATH}"), "cp (destination)"),
    (re.compile(rf"\bsed\s+-i\S*\s+.+?\s+{_PATH}"), "sed -i (in-place edit)"),
    (re.compile(rf"\btee\s+(?:-[aA]\s+)?{_PATH}"), "tee"),
    (re.compile(rf"\btouch\s+{_PATH}"), "touch"),
    (re.compile(rf"\bchmod\s+\S+\s+{_PATH}"), "chmod"),
    (re.compile(rf"\bchown\s+\S+\s+{_PATH}"), "chown"),
    (re.compile(rf"\btruncate\s+\S+\s+{_PATH}"), "truncate"),
]

# ---------------------------------------------------------------------------
# Dangerous git operations — blocked regardless of target path.
# Heartbeat-as-PR-agent must never push to main; force-pushes and
# reset --hard origin/main are destructive and banned.
# ---------------------------------------------------------------------------

DANGEROUS_GIT: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bgit\s+push\s+(?:\S+\s+)*(?:origin\s+)?main(?:\s|:|$)"),
        "git push to 'main' is forbidden — use a feature branch + PR",
    ),
    (
        re.compile(r"\bgit\s+push\s+(?:\S+\s+)*(?:origin\s+)?master(?:\s|:|$)"),
        "git push to 'master' is forbidden — use a feature branch + PR",
    ),
    (
        re.compile(
            r"\bgit\s+push\s+(?:\S+\s+)*(?:-f\b|--force\b|--force-with-lease\b)"
        ),
        "git force-push is forbidden",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\s+(?:origin/)?(?:main|master)\b"),
        "git reset --hard on main/master is forbidden",
    ),
]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _normalise_target(target: str) -> str:
    """Lower-case and convert backslashes to forward slashes for matching."""
    return target.replace("\\", "/").lower()


def check_protected_writes(command: str) -> tuple[bool, str]:
    """Return (blocked, reason) if the command writes to a protected path."""
    for pattern, verb in WRITE_PATTERNS:
        for match in pattern.finditer(command):
            raw_target = match.group(2)
            normalised = _normalise_target(raw_target)

            # Allowlist check: if the target is inside a known sample /
            # mirror tree, it's an intentional copy of a protected file,
            # not the live file itself. Skip protection.
            if any(allow in normalised for allow in ALLOWLIST_SUBSTRINGS):
                continue

            for protected in PROTECTED_SUBSTRINGS:
                if protected in normalised:
                    return True, (
                        f"{verb} targets protected path '{raw_target}' "
                        f"(matches '{protected}'). If legitimate, use the "
                        f"Edit/Write tool (hook allowlist decides) or ask "
                        f"the user to stage manually. See lessons.md "
                        f"entry for 2026-04-22 (Bash hook gap)."
                    )
    return False, ""


def check_dangerous_git(command: str) -> tuple[bool, str]:
    """Return (blocked, reason) if the command is a dangerous git op."""
    for pattern, reason in DANGEROUS_GIT:
        if pattern.search(command):
            return True, reason
    return False, ""


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Fail open — we don't want a malformed payload to brick Bash.
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str) or not command:
        return 0

    blocked, reason = check_protected_writes(command)
    if blocked:
        print(
            json.dumps({"decision": "block", "reason": f"[bash-safety-hook] {reason}"})
        )
        print(f"[bash-safety-hook] BLOCKED: {reason}", file=sys.stderr)
        return 2

    blocked, reason = check_dangerous_git(command)
    if blocked:
        print(
            json.dumps({"decision": "block", "reason": f"[bash-safety-hook] {reason}"})
        )
        print(f"[bash-safety-hook] BLOCKED: {reason}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 — intentional fail-open
        # Defence-in-depth: never brick Bash because this hook has a bug.
        # Log to stderr so it's visible in Claude Code's hook output.
        print(f"[bash-safety-hook] hook error (failing open): {e}", file=sys.stderr)
        sys.exit(0)
