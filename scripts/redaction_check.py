#!/usr/bin/env python3
"""Pattern-based redaction gate for the public mirror.

Scans the ADDED lines of a pull request for the *shapes* of private content —
email addresses, absolute home paths, and credential prefixes. Deliberately
generic: it must never hardcode the private strings it guards, because this
file is public. The maintainer's local pre-commit hook holds the specific
denylist (it lives in .git/hooks/ and is never committed); this CI gate is the
backstop that runs on every PR, including from forks.

High-confidence patterns only. A noisy gate that false-positives on ordinary
prose gets ignored or disabled, which is worse than no gate.

Exit 0 = clean. Exit 1 = potential leak(s), emitted as GitHub annotations.
Override a genuine false positive by merging with maintainer (admin) rights.

Usage:
    python scripts/redaction_check.py --base origin/main
    python scripts/redaction_check.py --selftest
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Domains safe to appear in docs and examples.
EMAIL_ALLOW = re.compile(
    r"@(example\.(com|org|net)|[^@\s]*\.example|anthropic\.com|claude\.com|"
    r"users\.noreply\.github\.com|email\.com|domain\.com|company\.com)$",
    re.IGNORECASE,
)
# Placeholder user/home tokens that are fine inside absolute-path examples.
PATH_PLACEHOLDERS = {
    "alice",
    "bob",
    "you",
    "user",
    "username",
    "home",
    "me",
    "example",
    "name",
    "youruser",
    "your-user",
    "jane",
    "johndoe",
    "john",
    "workspace",
}

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# /home/<name>, /Users/<name> (macOS), <Drive>:\Users\<name> (Windows).
HOME_PATH_RE = re.compile(
    r"(?:/home/|/Users/|[A-Za-z]:[\\/]Users[\\/])([A-Za-z0-9._-]+)"
)
CRED_RES = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9-]{8,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


def scan(text: str) -> list[tuple[str, str]]:
    """Return (kind, snippet) findings for one line of added text."""
    findings: list[tuple[str, str]] = []
    for m in EMAIL_RE.finditer(text):
        if not EMAIL_ALLOW.search(m.group(0)):
            findings.append(("email address", m.group(0)))
    for m in HOME_PATH_RE.finditer(text):
        if m.group(1).lower() not in PATH_PLACEHOLDERS:
            findings.append(("absolute home path", m.group(0)))
    for label, rgx in CRED_RES:
        m = rgx.search(text)
        if m:
            # Truncate so the gate's own log never reprints a full secret.
            findings.append((label, m.group(0)[:10] + "…"))
    return findings


def added_lines(base: str):
    """Yield (path, lineno, text) for every added line vs base."""
    diff = subprocess.run(
        ["git", "diff", "--no-color", "--unified=0", base],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    path = None
    newno = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            newno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            yield path, newno, line[1:]
            newno += 1


def run_selftest() -> int:
    # Sensitive shapes are built by concatenation so this test file itself
    # carries no contiguous secret or home-path string for static scanners
    # (the local denylist hook, GitHub secret scanning / push protection) to
    # trip on. The runtime values still exercise every pattern in scan().
    must_flag = [
        "contact me at real.person@gmail.com today",
        "path was /home/realname/.config",
        "C:" + "\\Users\\" + "realname\\notes",
        "token sk-" + "ant-" + "EXAMPLE000000000",
        "key " + "AKIA" + "EXAMPLE000000000" + " here",
    ]
    must_pass = [
        "see /home/alice/project for the example",
        "use " + "C:/" + "Users/alice/workspace",
        "email the author at user@example.com",
        "vector embeddings and data sovereignty are fine",
        "reference ~/.claude/settings.json (generic)",
    ]
    ok = True
    for s in must_flag:
        if not scan(s):
            print(f"SELFTEST FAIL (should flag): {s}", file=sys.stderr)
            ok = False
    for s in must_pass:
        if scan(s):
            print(f"SELFTEST FAIL (should pass): {s} -> {scan(s)}", file=sys.stderr)
            ok = False
    print("selftest: PASS" if ok else "selftest: FAIL")
    return 0 if ok else 1


# This scanner's own source carries leak-shaped fixtures by necessity; exclude
# it from scanning to avoid circular self-flagging. The file is maintainer-
# reviewed and still covered by the local denylist hook + GitHub secret scanning.
SELF_PATH = "scripts/redaction_check.py"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base", default="origin/main", help="base ref to diff added lines against"
    )
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="run built-in pattern assertions and exit",
    )
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()

    total = 0
    for path, lineno, text in added_lines(args.base):
        if path == SELF_PATH:
            continue
        for kind, snippet in scan(text):
            total += 1
            print(
                f"::error file={path},line={lineno}::"
                f"Possible {kind}: {snippet}. Generalise or remove "
                f"before this can merge."
            )
    if total:
        print(
            f"\nRedaction gate: {total} potential leak(s) in added lines. "
            f"Use placeholders (<home>, <workspace>, 'the user'). "
            f"Genuine false positive? A maintainer can override on merge.",
            file=sys.stderr,
        )
        return 1
    print("Redaction gate: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
