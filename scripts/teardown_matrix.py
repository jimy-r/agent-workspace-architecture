#!/usr/bin/env python3
"""Generate the cross-case presence matrix in teardowns/README.md.

Every teardown page already carries its verdict in machine-readable header
lines — `Patterns present:` and `Patterns absent worth noting:` — and its
conversion in a `What changed here` section. Five readings against one pattern
set is the aggregate evidence the index promises ("which patterns show up
independently, which are absent even in strong designs") and never showed.

This script derives that aggregate rather than letting anyone hand-maintain it,
the same regenerate-don't-hand-edit discipline as `gen_llms_full.py`. It owns
three things in `teardowns/README.md` and nothing else: the number word in the
`## What N readings show` heading, the text between the
`<!-- teardown-matrix:start -->` / `<!-- teardown-matrix:end -->` markers, and
the Published table between the `<!-- teardown-published:start -->` /
`<!-- teardown-published:end -->` markers. Prose outside the markers is left
alone.

Each page's header also opens with an `In one line` field, one sentence saying
what the reading found, and carries a `By` field. The Published table prints
that sentence beside each page, and the teardown lines in `docs/llms.txt` are
written from it too, so the summary a reader meets on the index, in the
machine-readable listing and on the page is the same sentence.

The matrix is also read back into `PATTERNS.md`. Under each pattern's
`Where it lives` paragraph the script keeps one line, "Seen in N of M
teardowns · Practise: learn/0N". N counts the readings that found the pattern
fully present, so a partial verdict is not counted, and the line links the
matrix where the partial and absent verdicts show. The module is the one that
`learn/README.md` assigns the pattern to.

How a page's header is read, because the pages encode partial two ways:

    [7](../PATTERNS.md#...) (partial)          a bare marker, applying to the
                                               pattern immediately before it
    ... ([8](...), [10](...) and [15](...) partial)
                                               a group, applying to every
                                               pattern inside the parentheses

Any other parenthetical is prose and is ignored, which is why
"(several partially — see body)" on the 12-Factor page marks nothing.
Classification runs present > partial > absent > not assessed, so a pattern the
present line already placed keeps that verdict even when the absent line
discusses it too — the GPT-RAG page names 3, 8 and 17 as partial and then calls
out their unbuilt halves, and both statements are true of a partial pattern.

A pattern a page names on neither line is not assessed, which is different
from absent. The last column counts the readings that did assess each pattern,
and the legend names any pattern assessed in fewer than MIN_ASSESSED readings,
because a claim that a pattern is missing across subjects needs readings that
looked for it.

Usage:
    python scripts/teardown_matrix.py            # rewrite what it owns
    python scripts/teardown_matrix.py --check    # exit 1 if anything would change
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEARDOWNS = REPO / "teardowns"
INDEX = TEARDOWNS / "README.md"
PATTERNS = REPO / "PATTERNS.md"
LLMS = REPO / "docs" / "llms.txt"
LEARN = REPO / "learn" / "README.md"

START = "<!-- teardown-matrix:start -->"
END = "<!-- teardown-matrix:end -->"
PUB_START = "<!-- teardown-published:start -->"
PUB_END = "<!-- teardown-published:end -->"

# Where a teardown page lives on GitHub, which is the form llms.txt links.
BLOB = "https://github.com/jimy-r/agent-workspace-architecture/blob/main/teardowns/"

WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
}

PRESENT, PARTIAL, ABSENT, UNASSESSED = "✓", "~", "✗", "—"

# The fewest assessed readings on which the index says anything about a
# pattern across subjects.
MIN_ASSESSED = 3

HEADING = re.compile(r"(?m)^## What \w+ readings show$")
PATTERN_HEADING = re.compile(r"(?m)^## (\d+)\. (.+)$")
LINK = re.compile(r"\[(\d+)\]\(\.\./PATTERNS\.md#[^)]*\)")
TOKEN = re.compile(r"@(\d+)@")
PAREN = re.compile(r"\(([^()]*)\)")
TITLE = re.compile(r"(?m)^# Teardown: (.+)$")
PRESENT_LINE = re.compile(r"(?m)^- \*\*Patterns present:\*\*(.*)$")
ABSENT_LINE = re.compile(r"(?m)^- \*\*Patterns absent worth noting:\*\*(.*)$")
CHANGED_SECTION = re.compile(
    r"(?ms)^## What changed here\s*$\n(.*?)(?=^## |^---\s*$|\Z)"
)
CHANGED_INLINE = re.compile(r"(?m)^\*\*What changed here:\*\*\s*(.+)$")
COMMENT = re.compile(r"(?s)<!--.*?-->")
SENTENCE = re.compile(r"(?<=[.!?])\s+")
NOTHING = re.compile(r"^(nothing yet|none|no change)\b", re.IGNORECASE)
FIELD = re.compile(r"(?m)^- \*\*([^*]+):\*\*")
ONE_LINE = re.compile(r"(?m)^- \*\*In one line:\*\* (.+)$")
BY_LINE = re.compile(r"(?m)^- \*\*By:\*\* \S")
DATE_LINE = re.compile(r"(?m)^- \*\*Date:\*\* (\d{4}-\d{2}-\d{2})\s*$")
REVISION = re.compile(r"(?m)^- \*\*Revision read:\*\* `([^`]+)`")
WHERE = "**Where it lives:**"
SEEN = re.compile(
    r"\[Seen in \d+ of \d+ teardowns\]\([^)]*\) · "
    r"Practise: \[learn/\d\d\]\([^)]*\)"
)
MODULE_LINK = re.compile(r"\[M\d+\.[^\]]*\]\((\d\d-[^)]+\.md)\)")
LLMS_ROW = re.compile(
    r"- \[[^\]]+\]\(" + re.escape(BLOB) + r"\d{4}-\d{2}-\d{2}-[^)]+\.md\): .*"
)


def short_name(title: str) -> str:
    """The title up to its first subordinate clause, for a table label."""
    cut = len(title)
    for mark in (",", " — ", ":", " ("):
        found = title.find(mark)
        if found != -1:
            cut = min(cut, found)
    return title[:cut].strip()


def load_patterns() -> list[tuple[int, str, str]]:
    """(number, short name, anchor) for every pattern, in file order.

    The anchor is the stable `pN` id PATTERNS.md sets above each heading, so a
    retitle never breaks the matrix links.
    """
    text = PATTERNS.read_text(encoding="utf-8")
    rows = [
        (int(num), short_name(title), f"p{num}")
        for num, title in PATTERN_HEADING.findall(text)
    ]
    if not rows:
        sys.exit("PATTERNS.md has zero '## N. <title>' headings — format changed?")
    missing = [a for _, _, a in rows if f'<a id="{a}"></a>' not in text]
    if missing:
        sys.exit(f"PATTERNS.md lacks the anchors {missing} above its headings")
    return rows


def classify(text: str, rel: str) -> dict[int, str]:
    """Read one page's header lines into {pattern number: glyph}."""
    present_match = PRESENT_LINE.search(text)
    absent_match = ABSENT_LINE.search(text)
    if not present_match:
        sys.exit(f"{rel}: no '- **Patterns present:**' header line")
    if not absent_match:
        sys.exit(f"{rel}: no '- **Patterns absent worth noting:**' header line")

    line = LINK.sub(lambda m: f"@{m.group(1)}@", present_match.group(1))
    partial: set[int] = set()
    for paren in PAREN.finditer(line):
        inside = paren.group(1)
        numbers = [int(n) for n in TOKEN.findall(inside)]
        if numbers and "partial" in inside.lower():
            partial.update(numbers)
        elif not numbers and inside.strip().lower() in ("partial", "partially"):
            before = TOKEN.findall(line[: paren.start()])
            if before:
                partial.add(int(before[-1]))

    verdicts: dict[int, str] = {}
    for num in (int(n) for n in TOKEN.findall(line)):
        verdicts[num] = PARTIAL if num in partial else PRESENT
    if not verdicts:
        sys.exit(f"{rel}: the 'Patterns present' line names no pattern links")

    for num in (int(n) for n in LINK.findall(absent_match.group(1))):
        verdicts.setdefault(num, ABSENT)
    return verdicts


def conversion(text: str, rel: str) -> str:
    """The first sentence of a page's 'What changed here', as a table cell."""
    section = CHANGED_SECTION.search(text)
    inline = CHANGED_INLINE.search(text)
    if section:
        body = COMMENT.sub("", section.group(1)).strip()
    elif inline:
        body = inline.group(1).strip()
    else:
        sys.exit(
            f"{rel}: no 'What changed here' section — it is the field the "
            f"publish rule reads (see teardowns/README.md § Page conventions)"
        )
    if not body:
        return "_not yet recorded_"
    first = SENTENCE.split(body)[0].strip()
    if NOTHING.match(first):
        return "none"
    return first.replace("|", "\\|")


def header(text: str, rel: str) -> dict[str, str]:
    """The summary, date and revision a page's header block carries."""
    where = "(see teardowns/README.md § Page conventions)"
    first = FIELD.search(text)
    one = ONE_LINE.search(text)
    if not one or not first or first.group(1) != "In one line":
        sys.exit(f"{rel}: the header does not open with '- **In one line:**' {where}")
    summary = one.group(1).strip()
    if "|" in summary:
        sys.exit(f"{rel}: 'In one line' holds a pipe, which breaks the index table")
    if not summary.endswith(".") or len(SENTENCE.split(summary)) != 1:
        sys.exit(f"{rel}: 'In one line' is one sentence ending in a full stop {where}")
    if not BY_LINE.search(text):
        sys.exit(f"{rel}: no '- **By:**' header field {where}")
    date = DATE_LINE.search(text)
    if not date:
        sys.exit(f"{rel}: no '- **Date:** YYYY-MM-DD' header field")
    revision = REVISION.search(text)
    if not revision:
        sys.exit(f"{rel}: 'Revision read' does not open with a revision in backticks")
    return {"summary": summary, "date": date.group(1), "revision": revision.group(1)}


def load_pages() -> list[dict]:
    """Every teardown page, oldest first (the filenames are date-prefixed)."""
    paths = sorted(p for p in TEARDOWNS.glob("*.md") if p.name != "README.md")
    if not paths:
        sys.exit("teardowns/ holds no teardown pages — directory moved?")

    pages = []
    for path in paths:
        rel = f"teardowns/{path.name}"
        text = path.read_text(encoding="utf-8")
        title = TITLE.search(text)
        if not title:
            sys.exit(f"{rel}: no '# Teardown: <subject>' heading")
        pages.append(
            {
                "file": path.name,
                "subject": title.group(1).strip(),
                "verdicts": classify(text, rel),
                "changed": conversion(text, rel),
                **header(text, rel),
            }
        )
    return pages


def newest_first(pages: list[dict]) -> list[dict]:
    """Pages by reading date, newest first, and by file name within a day."""
    return sorted(pages, key=lambda p: (p["date"], p["file"]), reverse=True)


def render_published(pages: list[dict]) -> str:
    """The Published table: one row per page, newest first."""
    lines = ["| Date | Subject | In one line | Revision read |", "|---|---|---|---|"]
    for page in newest_first(pages):
        lines.append(
            f"| {page['date']} | [{page['subject']}]({page['file']}) "
            f"| {page['summary']} | `{page['revision']}` |"
        )
    return "\n".join(lines)


def build_llms(pages: list[dict]) -> str:
    """docs/llms.txt with its teardown lines rewritten from the pages."""
    lines = LLMS.read_text(encoding="utf-8").split("\n")
    rows = [i for i, line in enumerate(lines) if LLMS_ROW.fullmatch(line)]
    if not rows:
        sys.exit("docs/llms.txt: no teardown page lines found — format changed?")
    if rows != list(range(rows[0], rows[-1] + 1)):
        sys.exit("docs/llms.txt: the teardown page lines are not one unbroken run")
    fresh = [
        f"- [{p['subject']}]({BLOB}{p['file']}): {p['summary']} "
        f"Read at `{p['revision']}`."
        for p in newest_first(pages)
    ]
    return "\n".join(lines[: rows[0]] + fresh + lines[rows[-1] + 1 :])


def render(patterns, pages) -> str:
    """The generated block: the presence matrix, then the conversion table."""
    header = " | ".join(f"[{p['subject']}]({p['file']})" for p in pages)
    lines = [
        f"| Pattern | {header} | Assessed |",
        "|---" * (len(pages) + 2) + "|",
    ]
    unassessed = 0
    thin = []
    for num, name, anchor in patterns:
        verdicts = [p["verdicts"].get(num, UNASSESSED) for p in pages]
        assessed = sum(v != UNASSESSED for v in verdicts)
        unassessed += len(pages) - assessed
        label = f"[{num}. {name}](../PATTERNS.md#{anchor})"
        if assessed < MIN_ASSESSED:
            thin.append(label)
        cells = " | ".join(verdicts)
        lines.append(f"| {label} | {cells} | {assessed}/{len(pages)} |")

    floor = WORDS.get(MIN_ASSESSED, str(MIN_ASSESSED))
    under = (
        "Under that floor today: " + ", ".join(thin) + "."
        if thin
        else "No pattern is under that floor today."
    )
    lines += [
        "",
        f"{PRESENT} present · {PARTIAL} partial · {ABSENT} absent, and named as "
        f"worth noting · {UNASSESSED} not assessed. Derived from each page's "
        "header by [`scripts/teardown_matrix.py`](../scripts/teardown_matrix.py). "
        "Edit the pages, not this table.",
        "",
        "`Assessed` counts the readings that gave the pattern a verdict, and "
        f"{unassessed} of the {len(patterns) * len(pages)} cells have none. A "
        "reading that did not assess a pattern is no evidence that the pattern "
        "is missing, so nothing is claimed about a pattern across subjects on "
        f"fewer than {floor} assessed readings. {under}",
        "",
        "What each reading changed here, first line of its own answer:",
        "",
        "| Reading | What changed here |",
        "|---|---|",
    ]
    for page in pages:
        lines.append(f"| [{page['subject']}]({page['file']}) | {page['changed']} |")
    return "\n".join(lines)


def load_modules() -> dict[int, str]:
    """{pattern number: learn module file}, from the learn track's table."""
    lines = LEARN.read_text(encoding="utf-8").splitlines()

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    col = None
    for line in lines:
        if line.startswith("| Module "):
            head = [c.lower() for c in cells(line)]
            if "patterns" in head:
                col = head.index("patterns")
            break
    if col is None:
        sys.exit("learn/README.md: no module table header with a 'Patterns' column")

    modules: dict[int, str] = {}
    for row in (l for l in lines if l.startswith("| [M")):
        parts = cells(row)
        link = MODULE_LINK.match(parts[0])
        if not link:
            sys.exit(f"learn/README.md: no module file link in: {row}")
        for token in parts[col].split(","):
            token = token.strip()
            if token.isdigit():
                modules[int(token)] = link.group(1)
    return modules


def seen_line(num: int, pages: list[dict], modules: dict[int, str]) -> str:
    """The generated line under one pattern's 'Where it lives' paragraph."""
    if num not in modules:
        sys.exit(f"learn/README.md: no module covers pattern {num}")
    seen = sum(p["verdicts"].get(num) == PRESENT for p in pages)
    word = WORDS.get(len(pages), str(len(pages)))
    module = modules[num]
    return (
        f"[Seen in {seen} of {len(pages)} teardowns]"
        f"(teardowns/README.md#what-{word}-readings-show) · "
        f"Practise: [learn/{module[:2]}](learn/{module})"
    )


def build_patterns(patterns, pages: list[dict]) -> str:
    """PATTERNS.md with the line under every 'Where it lives' made current."""
    modules = load_modules()
    lines = PATTERNS.read_text(encoding="utf-8").split("\n")
    out: list[str] = []
    current: int | None = None
    done: list[int] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            heading = PATTERN_HEADING.match(line)
            current = int(heading.group(1)) if heading else None
        out.append(line)
        i += 1
        if current is None or not line.startswith(WHERE):
            continue
        # Drop the line a previous run wrote, then write this run's.
        if i + 1 < len(lines) and lines[i] == "" and SEEN.fullmatch(lines[i + 1]):
            i += 2
        out += ["", seen_line(current, pages, modules)]
        done.append(current)
    numbers = [num for num, _, _ in patterns]
    if done != numbers:
        missing = sorted(set(numbers) - set(done))
        sys.exit(
            f"PATTERNS.md: expected one '{WHERE}' paragraph in each pattern, "
            f"and found none or more than one in {missing or 'some section'}"
        )
    return "\n".join(out)


def build() -> dict[Path, str]:
    """Every file this run owns a part of, with the text it would hold."""
    patterns = load_patterns()
    pages = load_pages()
    text = INDEX.read_text(encoding="utf-8")

    if not HEADING.search(text):
        sys.exit(
            "teardowns/README.md: no '## What <word> readings show' heading — "
            "add the section above the index first"
        )
    if START not in text or END not in text:
        sys.exit(
            f"teardowns/README.md: missing the {START} / {END} markers — "
            "add them inside the section first"
        )

    word = WORDS.get(len(pages), str(len(pages)))
    text = HEADING.sub(f"## What {word} readings show", text, count=1)
    text, swapped = re.subn(
        rf"(?s){re.escape(START)}.*?{re.escape(END)}",
        lambda _: f"{START}\n{render(patterns, pages)}\n{END}",
        text,
        count=1,
    )
    if swapped != 1:
        sys.exit("teardowns/README.md: could not rewrite the marked block")
    text, swapped = re.subn(
        rf"(?s){re.escape(PUB_START)}.*?{re.escape(PUB_END)}",
        lambda _: f"{PUB_START}\n{render_published(pages)}\n{PUB_END}",
        text,
        count=1,
    )
    if swapped != 1:
        sys.exit(
            f"teardowns/README.md: missing the {PUB_START} / {PUB_END} markers "
            "around the Published table"
        )
    return {
        INDEX: text,
        LLMS: build_llms(pages),
        PATTERNS: build_patterns(patterns, pages),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed files match the pages; do not write",
    )
    args = parser.parse_args()

    stale = [
        path
        for path, content in build().items()
        if path.read_text(encoding="utf-8") != content
    ]
    names = ", ".join(p.relative_to(REPO).as_posix() for p in stale)

    if args.check:
        if stale:
            print(
                f"STALE: {names} is out of date with the teardown pages. "
                "Run: python scripts/teardown_matrix.py",
                file=sys.stderr,
            )
            return 1
        print("Everything generated from the teardown pages matches them.")
        return 0

    if not stale:
        print("Everything generated from the teardown pages is already current.")
        return 0

    for path, content in build().items():
        if path in stale:
            path.write_text(content, encoding="utf-8")
    print(f"Rewrote {names}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
