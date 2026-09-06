#!/usr/bin/env python3
"""Check (or fix) the repo's hand-maintained freshness stamps against git.

Four stamps on the reader surface claim a date: the README footer, the tour's
JSON-LD `dateModified`, the tour's no-JS "Last updated" fallback, and every
`<lastmod>` in the sitemap. All four are hand-edited, all four have drifted
inside a single week, and a reader who trusts a stale stamp is being told the
page was verified on a day it was not.

The ground truth is git: a stamp must be at least as new as the last commit
that touched the file the stamp describes. Note "describes", not "contains" —
`docs/sitemap.xml` carries lastmod dates for the *pages* it lists, so each
entry is checked against its own page, not against the sitemap.

Usage:
    python scripts/check_freshness.py            # report drift, exit 1 if any
    python scripts/check_freshness.py --fix      # rewrite every stale stamp
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = "https://jimy-r.github.io/agent-workspace-architecture/"

# (file holding the stamp, regex with one date group, file the stamp describes)
# A stamp that describes its own file uses the same path twice.
STAMPS = [
    (
        "README.md",
        r"(?m)^\*Last verified against the repo structure on (\d{4}-\d{2}-\d{2})\.\*$",
        "README.md",
    ),
    (
        "docs/index.html",
        r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})"',
        "docs/index.html",
    ),
    (
        "docs/index.html",
        r'<span id="last-updated">Last updated: (\d{4}-\d{2}-\d{2})</span>',
        "docs/index.html",
    ),
]

# Sitemap entries are checked page by page: the loc URL maps back to the file
# under docs/ that Pages serves it from.
SITEMAP = "docs/sitemap.xml"


def last_commit_date(path: str) -> str | None:
    """Date (YYYY-MM-DD) of the newest commit touching `path`, or None."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", path],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    date = out.stdout.strip()
    return date or None


def loc_to_path(loc: str) -> str | None:
    """Map a sitemap <loc> back to the repo file Pages serves it from."""
    if not loc.startswith(SITE):
        return None
    tail = loc[len(SITE) :].strip("/")
    return f"docs/{tail}" if tail else "docs/index.html"


def collect() -> list[tuple[str, str, str, str, str]]:
    """Return (holder, described, stamp, expected, label) for every stamp."""
    rows: list[tuple[str, str, str, str, str]] = []

    for holder, pattern, described in STAMPS:
        text = (REPO / holder).read_text(encoding="utf-8")
        match = re.search(pattern, text)
        if not match:
            sys.exit(
                f"{holder}: stamp pattern not found — did the markup change?\n  {pattern}"
            )
        expected = last_commit_date(described)
        if expected:
            rows.append(
                (holder, described, match.group(1), expected, match.group(0)[:48])
            )

    sitemap = (REPO / SITEMAP).read_text(encoding="utf-8")
    for block in re.findall(r"<url>.*?</url>", sitemap, re.DOTALL):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        mod = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", block)
        if not (loc and mod):
            continue
        described = loc_to_path(loc.group(1))
        if not described or not (REPO / described).exists():
            sys.exit(f"{SITEMAP}: <loc>{loc.group(1)}</loc> has no file under docs/")
        expected = last_commit_date(described)
        if expected:
            rows.append((SITEMAP, described, mod.group(1), expected, loc.group(1)))

    return rows


def fix() -> int:
    """Rewrite every stale stamp to its file's last-commit date."""
    changed = 0

    for holder, pattern, described in STAMPS:
        expected = last_commit_date(described)
        if not expected:
            continue
        path = REPO / holder
        text = path.read_text(encoding="utf-8")
        match = re.search(pattern, text)
        if not match or match.group(1) >= expected:
            continue
        start, end = match.span(1)
        path.write_text(text[:start] + expected + text[end:], encoding="utf-8")
        changed += 1

    path = REPO / SITEMAP
    sitemap = path.read_text(encoding="utf-8")

    def replace(block: str) -> str:
        nonlocal changed
        loc = re.search(r"<loc>(.*?)</loc>", block)
        mod = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", block)
        if not (loc and mod):
            return block
        described = loc_to_path(loc.group(1))
        expected = last_commit_date(described) if described else None
        if not expected or mod.group(1) >= expected:
            return block
        changed += 1
        return block.replace(
            f"<lastmod>{mod.group(1)}</lastmod>", f"<lastmod>{expected}</lastmod>"
        )

    path.write_text(
        re.sub(
            r"<url>.*?</url>", lambda m: replace(m.group(0)), sitemap, flags=re.DOTALL
        ),
        encoding="utf-8",
    )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix", action="store_true", help="rewrite stale stamps in place"
    )
    args = parser.parse_args()

    if args.fix:
        n = fix()
        print(
            f"Updated {n} stale stamp(s)."
            if n
            else "Every stamp is current; nothing to fix."
        )
        return 0

    stale = []
    for holder, described, stamp, expected, label in collect():
        if stamp < expected:
            stale.append(
                f"  {holder}: {label!r} says {stamp}, but {described} last changed {expected}"
            )

    if stale:
        print("Stale freshness stamps:\n" + "\n".join(stale))
        print("\nFix with: python scripts/check_freshness.py --fix")
        return 1

    print("OK: every freshness stamp is at least as new as the file it describes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
