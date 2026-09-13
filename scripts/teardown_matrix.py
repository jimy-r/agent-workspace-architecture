#!/usr/bin/env python3
"""Generate the cross-case presence matrix in teardowns/README.md.

Every teardown page already carries its verdict in machine-readable header
lines — `Patterns present:` and `Patterns absent worth noting:` — and its
conversion in a `What changed here` section. Five readings against one pattern
set is the aggregate evidence the index promises ("which patterns show up
independently, which are absent even in strong designs") and never showed.

This script derives that aggregate rather than letting anyone hand-maintain it,
the same regenerate-don't-hand-edit discipline as `gen_llms_full.py`. It owns
two things in `teardowns/README.md` and nothing else: the number word in the
`## What N readings show` heading, and the text between the
`<!-- teardown-matrix:start -->` / `<!-- teardown-matrix:end -->` markers.
Prose written below the end marker is left alone.

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

Usage:
    python scripts/teardown_matrix.py            # rewrite the block
    python scripts/teardown_matrix.py --check    # exit 1 if it would change
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

START = "<!-- teardown-matrix:start -->"
END = "<!-- teardown-matrix:end -->"

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


def slug(heading: str) -> str:
    """GitHub's anchor slug for a '## N. Title' heading, minus the '## '."""
    kept = "".join(c for c in heading.lower() if c.isalnum() or c in " -")
    return kept.strip().replace(" ", "-")


def short_name(title: str) -> str:
    """The title up to its first subordinate clause, for a table label."""
    cut = len(title)
    for mark in (",", " — ", ":", " ("):
        found = title.find(mark)
        if found != -1:
            cut = min(cut, found)
    return title[:cut].strip()


def load_patterns() -> list[tuple[int, str, str]]:
    """(number, short name, anchor) for every pattern, in file order."""
    text = PATTERNS.read_text(encoding="utf-8")
    rows = [
        (int(num), short_name(title), slug(f"{num}. {title}"))
        for num, title in PATTERN_HEADING.findall(text)
    ]
    if not rows:
        sys.exit("PATTERNS.md has zero '## N. <title>' headings — format changed?")
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
            }
        )
    return pages


def render(patterns, pages) -> str:
    """The generated block: the presence matrix, then the conversion table."""
    header = " | ".join(f"[{p['subject']}]({p['file']})" for p in pages)
    lines = [
        f"| Pattern | {header} |",
        "|---" * (len(pages) + 1) + "|",
    ]
    for num, name, anchor in patterns:
        cells = " | ".join(p["verdicts"].get(num, UNASSESSED) for p in pages)
        lines.append(f"| [{num}. {name}](../PATTERNS.md#{anchor}) | {cells} |")

    lines += [
        "",
        f"{PRESENT} present · {PARTIAL} partial · {ABSENT} absent, and named as "
        f"worth noting · {UNASSESSED} not assessed. Derived from each page's "
        "header by [`scripts/teardown_matrix.py`](../scripts/teardown_matrix.py). "
        "Edit the pages, not this table.",
        "",
        "What each reading changed here, first line of its own answer:",
        "",
        "| Reading | What changed here |",
        "|---|---|",
    ]
    for page in pages:
        lines.append(f"| [{page['subject']}]({page['file']}) | {page['changed']} |")
    return "\n".join(lines)


def build() -> str:
    """The full README text this run would produce."""
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
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed block matches the pages; do not write",
    )
    args = parser.parse_args()

    content = build()
    current = INDEX.read_text(encoding="utf-8")

    if args.check:
        if current != content:
            print(
                "STALE: teardowns/README.md's matrix is out of date with the "
                "teardown pages. Run: python scripts/teardown_matrix.py",
                file=sys.stderr,
            )
            return 1
        print("teardowns/README.md's matrix matches the teardown pages.")
        return 0

    if current == content:
        print("teardowns/README.md's matrix is already current.")
        return 0

    INDEX.write_text(content, encoding="utf-8")
    print("Rewrote the matrix in teardowns/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
