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

A fifth class of stamp works the other way round. Every teardown page carries
a `Re-check by:` date in its header, the day its reading stops being claimable
as current, and that one is checked against the calendar rather than against
git: a reading of a moving subject decays whether or not anyone edits the file.
A missing field fails too, so the convention cannot quietly lapse on the next
page. Neither is auto-fixable — the remedy is re-reading the subject and
restamping, or marking the page `ageing`/`superseded` — so `--fix` reports
these and leaves them alone.

The same calendar rule covers each page's Lifts table. A lift is a change the
reading produced or proposed, and a proposed one with no owner and no date is
a note nobody will read again. Every page carries the table, every row has an
owner and a status of done, declined or open, and an open row fails once its
`Re-check by` date passes. The remedy is to build the lift, decline it, or
move the date and say why.

A page published after 2026-10-03 also needs the `Verified` and `Maintainer
heads-up` header fields, and, when its subject lives on GitHub, at least one
citation linked to a line at a commit sha. The seven earlier pages sit in
GRANDFATHERED until their next re-read.

Usage:
    python scripts/check_freshness.py            # report drift, exit 1 if any
    python scripts/check_freshness.py --fix      # rewrite every stale stamp
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = "https://jimy-r.github.io/agent-workspace-architecture/"

# Teardown pages date their own reading, not their source. README.md is the
# index and the convention block, not a reading, so it carries the template
# placeholder rather than a real date.
TEARDOWNS = "teardowns"
RECHECK = re.compile(r"(?m)^- \*\*Re-check by:\*\* (\d{4}-\d{2}-\d{2})\s*$")

# Pages published before the citation and review-field rules of 2026-10-03.
# Each is backfilled at its next re-read and then leaves this set; every other
# page must carry the Verified and Maintainer heads-up fields and cite the
# subject's GitHub source by line, pinned to a commit.
GRANDFATHERED = {
    "2026-08-27-12-factor-agents.md",
    "2026-08-28-herdr.md",
    "2026-08-28-lifeos.md",
    "2026-09-05-deepseek-harness.md",
    "2026-09-06-azure-gpt-rag.md",
    "2026-10-02-openharness.md",
    # Zenith was published before this rule reached main: fields present, paths cited bare.
    "2026-10-03-zenith.md",
}
VERIFIED = re.compile(
    r"(?m)^- \*\*Verified:\*\* \d{4}-\d{2}-\d{2}, \d+ citations? re-read\s*$"
)
HEADS_UP = re.compile(r"(?m)^- \*\*Maintainer heads-up:\*\* \S")
SUBJECT_REPO = re.compile(
    r"(?m)^- \*\*Subject:\*\* <?https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?/?>?\s*$"
)
BLOB_LINK = re.compile(
    r"https://github\.com/([\w.-]+/[\w.-]+)/blob/([^/\s)]+)/[^\s)#]+(#L\d+(?:-L\d+)?)?"
)
HEX_SHA = re.compile(r"[0-9a-f]{7,40}")
PAGES_HEAD = (
    "Teardown pages missing a review field or a line-pinned citation "
    "(teardowns/README.md § Page conventions):\n"
)

# The Lifts table every teardown page carries under "What changed here".
LIFTS_HEADER = "| Lift | Owner | Status | Re-check by |"
LIFT_STATUSES = ("done", "declined", "open")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

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


def expired_teardowns(today: str | None = None) -> list[str]:
    """Return one line per teardown whose `Re-check by` is past or missing."""
    today = today or date.today().isoformat()
    pages = sorted(p for p in (REPO / TEARDOWNS).glob("*.md") if p.name != "README.md")
    if not pages:
        sys.exit(f"{TEARDOWNS}/ holds no teardown pages — directory moved?")

    problems = []
    for page in pages:
        rel = f"{TEARDOWNS}/{page.name}"
        match = RECHECK.search(page.read_text(encoding="utf-8"))
        if not match:
            problems.append(
                f"  {rel}: no '- **Re-check by:** YYYY-MM-DD' header field "
                f"(see {TEARDOWNS}/README.md § Page conventions)"
            )
        elif match.group(1) < today:
            problems.append(
                f"  {rel}: re-check was due {match.group(1)}, today is {today}"
            )
    return problems


def new_page_problems(rel: str, text: str) -> list[str]:
    """Review fields and line-pinned citations, for one page outside GRANDFATHERED."""
    problems = []
    if not VERIFIED.search(text):
        problems.append(
            f"  {rel}: no '- **Verified:** YYYY-MM-DD, N citations re-read' header field"
        )
    if not HEADS_UP.search(text):
        problems.append(f"  {rel}: no '- **Maintainer heads-up:**' header field")
    subject = SUBJECT_REPO.search(text)
    if subject:
        repo = subject.group(1).lower()
        links = [m for m in BLOB_LINK.finditer(text) if m.group(1).lower() == repo]
        if not any(m.group(3) for m in links):
            problems.append(
                f"  {rel}: no citation of the form "
                f"https://github.com/{subject.group(1)}/blob/<sha>/<path>#L<n>"
            )
        for m in links:
            if not HEX_SHA.fullmatch(m.group(2)):
                problems.append(
                    f"  {rel}: citation pinned to '{m.group(2)}', not a commit sha: {m.group(0)}"
                )
    return problems


def page_problems() -> list[str]:
    """Apply new_page_problems to every teardown page published after the rules."""
    pages = sorted(p for p in (REPO / TEARDOWNS).glob("*.md") if p.name != "README.md")
    problems = []
    for page in pages:
        if page.name in GRANDFATHERED:
            continue
        rel = f"{TEARDOWNS}/{page.name}"
        problems += new_page_problems(rel, page.read_text(encoding="utf-8"))
    return problems


def lift_rows(text: str) -> list[list[str]] | None:
    """The cells of each row in a page's Lifts table, or None with no table."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == LIFTS_HEADER)
    except StopIteration:
        return None
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        # A literal pipe inside a cell is written \| in a markdown table.
        cells = line.strip().strip("|").replace("\\|", "\x00").split("|")
        rows.append([c.replace("\x00", "|").strip() for c in cells])
    return rows


def lift_problems(today: str | None = None) -> list[str]:
    """Return one line per teardown lift that is malformed or open past its date."""
    today = today or date.today().isoformat()
    pages = sorted(p for p in (REPO / TEARDOWNS).glob("*.md") if p.name != "README.md")

    problems = []
    for page in pages:
        rel = f"{TEARDOWNS}/{page.name}"
        rows = lift_rows(page.read_text(encoding="utf-8"))
        if not rows:
            problems.append(
                f"  {rel}: no Lifts table with at least one row "
                f"(see {TEARDOWNS}/README.md § Page conventions)"
            )
            continue
        for row in rows:
            if len(row) != 4:
                problems.append(f"  {rel}: a Lifts row has {len(row)} cells, not 4")
                continue
            lift, owner, status, recheck = row
            name = lift if len(lift) <= 60 else lift[:57] + "..."
            if not owner:
                problems.append(f"  {rel}: lift '{name}' has no owner")
            if status not in LIFT_STATUSES:
                problems.append(
                    f"  {rel}: lift '{name}' has status '{status}', expected one of "
                    + ", ".join(LIFT_STATUSES)
                )
            elif status == "open":
                if not ISO_DATE.fullmatch(recheck):
                    problems.append(
                        f"  {rel}: open lift '{name}' has no YYYY-MM-DD re-check date"
                    )
                elif recheck < today:
                    problems.append(
                        f"  {rel}: open lift '{name}' was due a re-check on "
                        f"{recheck}, today is {today}"
                    )
    return problems


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
    parser.add_argument(
        "--teardowns",
        action="store_true",
        help="check only the teardown re-check dates and Lifts tables (a calendar gate, safe on a schedule)",
    )
    args = parser.parse_args()

    expired = expired_teardowns()
    lifts = lift_problems()
    pages = page_problems()

    if args.teardowns:
        if expired:
            print("Teardown readings past their re-check date:\n" + "\n".join(expired))
        if lifts:
            print("Teardown lifts that need attention:\n" + "\n".join(lifts))
        if pages:
            print(PAGES_HEAD + "\n".join(pages))
        if expired or lifts or pages:
            return 1
        print(
            "Every teardown reading is inside its re-check date, "
            "and no open lift is past its own."
        )
        return 0

    if args.fix:
        n = fix()
        print(
            f"Updated {n} stale stamp(s)."
            if n
            else "Every stamp is current; nothing to fix."
        )
        if expired:
            # Not auto-fixable: the remedy is re-reading the subject, so say so
            # rather than exiting green on a check --fix cannot satisfy.
            print(
                "\nTeardown readings past their re-check date (--fix cannot "
                "repair these):\n" + "\n".join(expired)
            )
        if lifts:
            print(
                "\nTeardown lifts that need attention (--fix cannot repair "
                "these):\n" + "\n".join(lifts)
            )
        if pages:
            print("\n" + PAGES_HEAD + "\n".join(pages))
        return 0

    stale = []
    for holder, described, stamp, expected, label in collect():
        if stamp < expected:
            stale.append(
                f"  {holder}: {label!r} says {stamp}, but {described} last changed {expected}"
            )

    failed = False
    if stale:
        print("Stale freshness stamps:\n" + "\n".join(stale))
        print("\nFix with: python scripts/check_freshness.py --fix")
        failed = True

    if expired:
        print("Teardown readings past their re-check date:\n" + "\n".join(expired))
        print(
            "\nRe-read the subject and restamp `Re-check by`, or set `Status` to "
            "ageing/superseded and say what replaced it."
        )
        failed = True

    if pages:
        print(PAGES_HEAD + "\n".join(pages))
        failed = True

    if lifts:
        print("Teardown lifts that need attention:\n" + "\n".join(lifts))
        print(
            "\nBuild an overdue lift, decline it, or move its date and say why. "
            "Every page needs the table (teardowns/README.md § Page conventions)."
        )
        failed = True

    if failed:
        return 1

    print(
        "OK: every freshness stamp is at least as new as the file it describes, "
        "every teardown reading is inside its re-check date, and no open lift "
        "is past its own."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
