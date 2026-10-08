#!/usr/bin/env python3
"""Generate docs/patterns/ from PATTERNS.md: one titled HTML page per pattern.

The Pages site served two HTML pages, so no pattern had a page of its own on
the site's host. This script renders each `## N. <title>` section of
`PATTERNS.md` as a page under `docs/patterns/`, plus an index page that carries
the document's opening paragraphs and every closing section.

The markdown stays the source of truth. Nothing on a generated page is written
here except navigation labels. A page's title is the pattern's heading, its
meta description is the first sentence of the pattern's Problem paragraph, and
its body is the section rendered construct for construct. A markdown construct
the renderer does not know stops the run, so nothing is published half-rendered.

File names are pinned in SLUGS and never derived again, so a retitle in
`PATTERNS.md` does not move a published URL. A new pattern needs one new line
there, and the run prints it.

The colour tokens and the favicon are read out of `docs/index.html` on every
run, so the pages follow the tour's look instead of keeping a copy of it. The
relative-link resolver is the one `gen_llms_full.py` uses.

`docs/sitemap.xml` is hand-maintained, and its dates belong to
`check_freshness.py`. This script only checks that the sitemap lists every
page it writes.

Usage:
    python scripts/gen_pattern_pages.py            # write docs/patterns/
    python scripts/gen_pattern_pages.py --check    # exit 1 if anything is stale
    python scripts/gen_pattern_pages.py --selftest # assert the renderer
"""

from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from gen_llms_full import ABSOLUTE, BLOB, SITE, resolve_link

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "PATTERNS.md"
DOCS = REPO / "docs"
OUT = DOCS / "patterns"
TOUR = DOCS / "index.html"
SITEMAP = DOCS / "sitemap.xml"

SITE_NAME = "Agent Workspace Architecture"
REPO_URL = BLOB.partition("/blob/")[0]
SECTION_URL = f"{SITE}patterns/"
SOCIAL_CARD = f"{SITE}assets/social-card.png"
STYLESHEET = "patterns.css"
ME = "scripts/gen_pattern_pages.py"

# Pattern number -> page file name, without the extension. Pinned: a published
# URL outlives the title it was first derived from. Add a line for a new
# pattern and leave the old ones alone.
#
# Each name is the heading in lower case with hyphens, except 6. `.gitignore`
# drops any path holding the plural of "credential", so that name would never
# reach a commit, and it is pinned in the singular. ignored_files() refuses the
# next name that collides the same way.
SLUGS = {
    1: "01-pure-roles-composed-with-project-facts",
    2: "02-classify-then-act-not-ask-then-wait",
    3: "03-make-silent-failure-loud-the-dead-mans-switch",
    4: "04-tier-by-mechanical-impact-not-by-tone",
    5: "05-memory-points-it-doesnt-mirror",
    6: "06-credential-lives-in-one-place-never-in-files",
    7: "07-a-cheap-hook-beats-a-careful-agent",
    8: "08-audit-the-workspace-like-a-fitness-function",
    9: "09-context-is-a-budget-not-a-constant",
    10: "10-a-skill-is-editable-weights-never-adopt-a-self-edit-without-a-gate",
    11: "11-a-scaffold-is-a-hypothesis-gate-it-behind-a-measurable-signal",
    12: "12-loop-selection-not-everything-should-be-a-loop",
    13: "13-challenge-half-formed-ideas-with-a-different-lens",
    14: "14-delegation-is-a-queue-you-fill-not-work-the-agent-finds",
    15: "15-price-the-lane-before-you-migrate-it",
    16: "16-a-claim-carries-its-provenance-or-it-is-a-guess",
    17: "17-one-canonical-copy-and-pointers-from-everywhere-else",
    18: "18-position-is-price-a-token-costs-more-the-earlier-you-add-it",
}
SLUG = re.compile(r"\d{2,}-[a-z0-9]+(?:-[a-z0-9]+)*")

# The index table in PATTERNS.md links each pattern to its in-page anchor. The
# site's index page is that same list with page links, so the section is
# rebuilt from the patterns and its markdown is not rendered.
INDEX_HEADING = "Index"
PATTERN_HEADING = re.compile(r"(\d+)\. (.+)")
ANCHOR = re.compile(r'<a id="p(\d+)"></a>')
PROBLEM = "**Problem.**"

# Everything after the closing rule is the markdown file's own freshness
# footer. It dates the file, not these pages, so it is not rendered.
FOOTER = re.compile(
    r"\*Last verified against the repo structure on \*{0,2}\d{4}-\d{2}-\d{2}\*{0,2}\.\*"
)

# Block constructs the source does not use today. Each one stops the run.
UNSUPPORTED = re.compile(r"(?: {4}|\t|#|>|\||[-*+] |\d+[.)] |```|~~~|<)")

# Inline constructs, tried in this order at each position: a code span, a
# link whose text may hold code spans, strong emphasis, emphasis.
INLINE = re.compile(
    r"`(?P<code>[^`\n]+)`"
    r"|\[(?P<text>(?:`[^`\n]+`|[^\[\]`])+)\]\((?P<href>[^()\s]+)\)"
    r"|\*\*(?P<strong>.+?)\*\*"
    r"|\*(?P<em>[^*\n]+)\*"
)
LABEL = re.compile(r"\*\*([^*]+)\*\*")
LEFTOVER = re.compile(r"[*`]|\]\(")
SENTENCE = re.compile(r"(.+?[.!?][\"')\]]*)(?:\s+(?=[A-Z0-9\"'(\[])|\s*$)", re.DOTALL)

# The tokens the stylesheet below reads. All of them come from the tour.
TOKENS = (
    "--ink",
    "--oxblood",
    "--oxblood-soft",
    "--paper",
    "--card",
    "--muted",
    "--rule",
    "--shadow",
)

STYLE = """\
*{box-sizing:border-box;}
body{margin:0; background:var(--paper); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; font-size:17px; line-height:1.6; -webkit-font-smoothing:antialiased;}
a{color:var(--oxblood); text-decoration:none;}
a:hover{text-decoration:underline;}
h1,h2{font-family:Georgia,"Times New Roman",serif;}
.wrap{max-width:780px; margin:0 auto; padding:0 22px;}
.eyebrow{font-size:12.5px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--oxblood); margin:0 0 14px;}

/* nav */
nav.top{position:sticky; top:0; z-index:30; background:var(--paper); background:color-mix(in srgb,var(--paper) 90%,transparent); backdrop-filter:saturate(140%) blur(8px); border-bottom:1px solid var(--rule);}
nav.top .wrap{display:flex; align-items:center; gap:18px; height:56px;}
nav.top .brand{font-family:Georgia,serif; font-weight:700; font-size:16px; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0;}
nav.top .links{display:flex; gap:16px; margin-left:auto; align-items:center; flex:0 0 auto;}
nav.top .links a{color:var(--ink); font-size:14px; font-weight:500; white-space:nowrap;}
nav.top .links a[aria-current]{color:var(--oxblood);}
@media (max-width:720px){ nav.top .links a.hideable{display:none;} }

/* text */
main.wrap{padding-top:56px; padding-bottom:28px;}
h1{font-size:38px; line-height:1.1; letter-spacing:-.6px; margin:0 0 26px;}
h2{font-size:26px; line-height:1.2; letter-spacing:-.3px; margin:52px 0 14px;}
main p{margin:0 0 18px; overflow-wrap:break-word;}
main p a{text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px;}
strong.k{color:var(--oxblood);}
code{font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace; font-size:.86em; background:var(--card); border:1px solid var(--rule); border-radius:5px; padding:1px 5px; overflow-wrap:anywhere;}
@media (max-width:560px){ h1{font-size:31px;} h2{font-size:23px;} }

/* cards: the index list and the pager */
.doc{background:var(--card); border:1px solid var(--rule); border-radius:11px; padding:16px 18px; display:block;}
.doc:hover{border-color:var(--oxblood-soft); text-decoration:none; box-shadow:var(--shadow);}
.doc .dt{display:block; font-family:Georgia,serif; font-weight:700; font-size:16.5px; line-height:1.3; color:var(--ink);}
.doc .dd{display:block; font-size:14.5px; color:var(--muted); margin-top:4px;}
.doc .dir{display:block; font-size:11.5px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--oxblood); margin-bottom:4px;}
.plist{list-style:none; margin:34px 0 0; padding:0; display:grid; grid-template-columns:minmax(0,1fr); gap:12px;}
.plist .doc{display:flex; gap:14px; align-items:baseline;}
.plist .num{font-family:Georgia,serif; font-weight:700; color:var(--oxblood); font-size:15px; flex:0 0 auto;}
.pager{display:grid; grid-template-columns:minmax(0,1fr); gap:12px; margin:44px 0 0; padding-top:28px; border-top:1px solid var(--rule);}
@media (min-width:680px){ .pager{grid-template-columns:minmax(0,1fr) minmax(0,1fr);} .pager .next{grid-column:2; text-align:right;} }
.source{font-size:14.5px; color:var(--muted); margin:22px 0 0;}

footer{padding:22px 0 56px; color:var(--muted); font-size:13.5px;}
footer .wrap{display:flex; gap:14px; flex-wrap:wrap; align-items:center;}
footer a{color:var(--muted);}
"""


@dataclass(frozen=True)
class Pattern:
    number: int
    title: str
    blocks: tuple[str, ...]
    slug: str

    @property
    def page(self) -> str:
        return f"{self.slug}.html"

    @property
    def heading(self) -> str:
        return f"{self.number}. {self.title}"


def fail(message: str) -> SystemExit:
    return SystemExit(f"ERROR: {message}")


# ---------------------------------------------------------------- the source


def parse(text: str) -> tuple[str, list[str], list[tuple[str, list[str], str | None]]]:
    """Split the document into its title, opening paragraphs and `##` sections.

    Each section is (heading, paragraphs, the number of the `pN` anchor placed
    above the heading or None). A paragraph is the raw markdown of one block.
    """
    title = ""
    intro: list[str] = []
    sections: list[tuple[str, list[str], str | None]] = []
    blocks = intro
    para: list[str] = []
    anchor: str | None = None
    footer = False

    def flush() -> None:
        if para:
            blocks.append("\n".join(para))
            para.clear()

    for number, line in enumerate(text.split("\n"), 1):
        where = f"PATTERNS.md:{number}"
        stripped = line.strip()
        if footer:
            if stripped and not FOOTER.fullmatch(stripped):
                raise fail(
                    f"{where}: content after the closing rule that is not the "
                    "freshness footer. Nothing below the rule is rendered."
                )
            continue
        if not stripped:
            flush()
            continue
        if line.startswith("# "):
            if title or intro or sections or para:
                raise fail(f"{where}: a second top-level heading")
            title = stripped[2:]
            continue
        if line.startswith("## "):
            flush()
            heading = stripped[3:]
            if anchor is not None and not heading.startswith(f"{anchor}. "):
                raise fail(f"{where}: the anchor p{anchor} sits above '{heading}'")
            blocks = []
            sections.append((heading, blocks, anchor))
            anchor = None
            continue
        match = ANCHOR.fullmatch(stripped)
        if match:
            flush()
            anchor = match.group(1)
            continue
        if stripped == "---":
            flush()
            footer = True
            continue
        if sections and sections[-1][0] == INDEX_HEADING:
            continue
        if UNSUPPORTED.match(line):
            raise fail(
                f"{where}: a markdown construct this script does not render "
                f"({stripped[:40]!r}). Teach {ME} the construct before publishing it."
            )
        para.append(stripped)
    flush()

    if not title:
        raise fail("PATTERNS.md has no '# <title>' heading")
    return title, intro, sections


def suggest_slug(number: int, title: str) -> str:
    """The file name a new pattern would be pinned to."""
    words = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("'", "")).strip("-")
    return f"{number:02d}-{words}"


def heading_anchor(heading: str) -> str:
    """The fragment GitHub gives a markdown heading."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def load(
    text: str,
) -> tuple[str, list[str], list[Pattern], list[tuple[str, list[str]]]]:
    """Return (title, opening paragraphs, patterns, closing sections)."""
    title, intro, sections = parse(text)
    patterns: list[Pattern] = []
    closing: list[tuple[str, list[str]]] = []
    unpinned: list[str] = []

    for heading, blocks, anchor in sections:
        match = PATTERN_HEADING.fullmatch(heading)
        if not match:
            if heading != INDEX_HEADING:
                closing.append((heading, blocks))
            continue
        number, name = int(match.group(1)), match.group(2)
        if anchor is None:
            raise fail(
                f'pattern {number} has no <a id="p{number}"></a> line above its '
                "heading, and its page links back to that anchor"
            )
        if patterns and number <= patterns[-1].number:
            raise fail(f"pattern {number} is out of order or numbered twice")
        if number not in SLUGS:
            unpinned.append(f'    {number}: "{suggest_slug(number, name)}",')
            continue
        patterns.append(Pattern(number, name, tuple(blocks), SLUGS[number]))

    if unpinned:
        raise fail(
            f"no pinned file name for a pattern. Add to SLUGS in {ME}:\n"
            + "\n".join(unpinned)
        )
    if not patterns:
        raise fail("PATTERNS.md has zero '## N. <title>' headings - format changed?")
    return title, intro, patterns, closing


def check_pins(patterns: list[Pattern]) -> None:
    """Refuse a SLUGS table that is malformed or pins a pattern that is gone."""
    orphans = sorted(set(SLUGS) - {p.number for p in patterns})
    if orphans:
        raise fail(f"SLUGS pins patterns PATTERNS.md does not have: {orphans}")
    for number, slug in SLUGS.items():
        if not SLUG.fullmatch(slug) or not slug.startswith(f"{number:02d}-"):
            raise fail(f"SLUGS[{number}] = {slug!r} is not '{number:02d}-<words>'")
    if len(set(SLUGS.values())) != len(SLUGS):
        raise fail("SLUGS pins one file name to two patterns")


# ------------------------------------------------------------------- inline


def text_node(text: str) -> str:
    """Escape plain text, refusing markdown the inline pass left behind."""
    if LEFTOVER.search(text):
        raise fail(
            f"unrendered markdown in {text.strip()[:60]!r}. Unbalanced emphasis, "
            "or an inline construct this script does not render."
        )
    return html.escape(text, quote=False)


def render_inline(text: str, href: Callable[[str], str]) -> str:
    """One paragraph's markdown as HTML."""
    out: list[str] = []
    position = 0
    for match in INLINE.finditer(text):
        out.append(text_node(text[position : match.start()]))
        if match.group("code") is not None:
            out.append(f"<code>{html.escape(match.group('code'), quote=False)}</code>")
        elif match.group("href") is not None:
            target = html.escape(href(match.group("href")), quote=True)
            out.append(
                f'<a href="{target}">{render_inline(match.group("text"), href)}</a>'
            )
        elif match.group("strong") is not None:
            out.append(f"<strong>{render_inline(match.group('strong'), href)}</strong>")
        else:
            out.append(f"<em>{render_inline(match.group('em'), href)}</em>")
        position = match.end()
    out.append(text_node(text[position:]))
    return "".join(out)


def plain_text(text: str) -> str:
    """One paragraph's markdown with the markup removed."""

    def unwrap(match: re.Match[str]) -> str:
        if match.group("code") is not None:
            return match.group("code")
        return plain_text(
            match.group("text") or match.group("strong") or match.group("em")
        )

    return INLINE.sub(unwrap, text)


def first_sentence(text: str) -> str:
    """The first sentence of plain text, or all of it when there is one."""
    text = " ".join(text.split())
    match = SENTENCE.match(text)
    return match.group(1) if match else text


def render_block(block: str, href: Callable[[str], str]) -> str:
    """One paragraph. A leading bold run is the paragraph's label."""
    label = LABEL.match(block)
    if label:
        rest = render_inline(block[label.end() :], href)
        return f'<p><strong class="k">{render_inline(label.group(1), href)}</strong>{rest}</p>'
    return f"<p>{render_inline(block, href)}</p>"


def description_of(pattern: Pattern) -> str:
    """The first sentence of the pattern's Problem paragraph, as plain text."""
    for block in pattern.blocks:
        if block.startswith(PROBLEM):
            return first_sentence(plain_text(block[len(PROBLEM) :]))
    raise fail(
        f"pattern {pattern.number} has no '{PROBLEM}' paragraph to take its "
        "description from"
    )


def link_resolver(patterns: list[Pattern]) -> Callable[[str], str]:
    """Map a link target written in PATTERNS.md to an href on a generated page.

    A fragment that names a pattern goes to that pattern's page. Any other
    fragment goes to the markdown file on the repo browser, and a relative path
    goes wherever `gen_llms_full.resolve_link` sends it.
    """
    pages: dict[str, str] = {}
    for pattern in patterns:
        pages[f"p{pattern.number}"] = pattern.page
        pages[heading_anchor(pattern.heading)] = pattern.page

    def href(target: str) -> str:
        if target.startswith("#"):
            return pages.get(target[1:]) or f"{BLOB}PATTERNS.md{target}"
        return resolve_link(target, "PATTERNS.md") or target

    return href


# -------------------------------------------------------------------- pages


def tour_look() -> tuple[str, str]:
    """Return the tour's `:root` token block and its favicon link."""
    tour = TOUR.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{([^}]*)\}", tour)
    icon = re.search(r'<link rel="icon" href="[^"]+">', tour)
    if not (root and icon):
        raise fail(
            "docs/index.html: no ':root{...}' token block or no "
            '<link rel="icon"> - did the markup change?'
        )
    declarations = [d.strip() for d in root.group(1).split(";") if d.strip()]
    missing = [
        t for t in TOKENS if not any(d.startswith(f"{t}:") for d in declarations)
    ]
    if missing:
        raise fail(f"docs/index.html no longer defines {', '.join(missing)}")
    block = ":root{\n" + "".join(f"  {d};\n" for d in declarations) + "}\n"
    return block, icon.group(0)


def stylesheet(tokens: str) -> str:
    return (
        f"/* Generated by {ME}. The :root tokens are read from\n"
        "   docs/index.html on every run, so change them there. */\n"
        f"{tokens}{STYLE}"
    )


def head(
    title: str, description: str, url: str, kind: str, data: dict, icon: str
) -> str:
    attr = html.escape(description, quote=True)
    name = html.escape(title, quote=True)
    linked = json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title, quote=False)} — {SITE_NAME}</title>
<meta name="description" content="{attr}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{name}">
<meta property="og:description" content="{attr}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SOCIAL_CARD}">
<meta name="twitter:card" content="summary_large_image">
{icon}
<link rel="stylesheet" href="{STYLESHEET}">
<script type="application/ld+json">
{linked}
</script>
<!-- Generated by {ME} from PATTERNS.md. Edit the markdown, not this file. -->
</head>
<body>
"""


def top_nav(on_index: bool) -> str:
    current = ' aria-current="page"' if on_index else ""
    return f"""
<nav class="top" aria-label="Primary">
  <div class="wrap">
    <a class="brand" href="../">{SITE_NAME}</a>
    <span class="links">
      <a href="../" class="hideable">Tour</a>
      <a href="./"{current}>Patterns</a>
      <a href="../workspace-map.html" class="hideable">The map</a>
      <a href="{REPO_URL}" class="hideable">GitHub</a>
    </span>
  </div>
</nav>
"""


FOOT = f"""
<footer>
  <div class="wrap">
    <a href="../">Tour</a>
    <a href="./">Patterns</a>
    <a href="{REPO_URL}">Repository</a>
    <a href="../llms.txt">llms.txt</a>
    <a href="../llms-full.txt">llms-full.txt</a>
  </div>
</footer>
</body>
</html>
"""


def pager_link(pattern: Pattern, side: str, label: str) -> str:
    return (
        f'    <a class="doc {side}" href="{pattern.page}">'
        f'<span class="dir">{label}</span>'
        f'<span class="dt">{html.escape(pattern.heading, quote=False)}</span></a>\n'
    )


def pattern_page(
    pattern: Pattern,
    before: Pattern | None,
    after: Pattern | None,
    section: str,
    href: Callable[[str], str],
    icon: str,
) -> str:
    url = f"{SECTION_URL}{pattern.page}"
    description = description_of(pattern)
    source = f"{BLOB}PATTERNS.md#p{pattern.number}"
    data = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": pattern.title,
        "description": description,
        "url": url,
        "mainEntityOfPage": url,
        "inLanguage": "en",
        "isPartOf": {"@type": "CollectionPage", "name": section, "url": SECTION_URL},
        "isBasedOn": source,
    }
    body = "".join(f"    {render_block(block, href)}\n" for block in pattern.blocks)
    pager = ""
    if before:
        pager += pager_link(before, "prev", "&larr; Previous")
    if after:
        pager += pager_link(after, "next", "Next &rarr;")
    return (
        head(pattern.heading, description, url, "article", data, icon)
        + top_nav(False)
        + f"""
<main class="wrap">
  <article>
    <p class="eyebrow">Pattern {pattern.number}</p>
    <h1>{html.escape(pattern.title, quote=False)}</h1>
{body}  </article>
  <nav class="pager" aria-label="Neighbouring patterns">
{pager}  </nav>
  <p class="source"><a href="./">All patterns</a> · <a href="{source}">Markdown source on GitHub</a></p>
</main>
"""
        + FOOT
    )


def index_page(
    title: str,
    intro: list[str],
    patterns: list[Pattern],
    closing: list[tuple[str, list[str]]],
    href: Callable[[str], str],
    icon: str,
) -> str:
    if not intro:
        raise fail("PATTERNS.md has no opening paragraph to describe the index page")
    description = first_sentence(plain_text(intro[0]))
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": SECTION_URL,
        "inLanguage": "en",
        "isBasedOn": f"{BLOB}PATTERNS.md",
        "hasPart": [
            {
                "@type": "TechArticle",
                "headline": pattern.title,
                "url": f"{SECTION_URL}{pattern.page}",
            }
            for pattern in patterns
        ],
    }
    opening = "".join(f"  {render_block(block, href)}\n" for block in intro)
    items = "".join(
        f'    <li><a class="doc" href="{pattern.page}">'
        f'<span class="num">{pattern.number:02d}</span><span>'
        f'<span class="dt">{html.escape(pattern.title, quote=False)}</span>'
        f'<span class="dd">{html.escape(description_of(pattern), quote=False)}</span>'
        "</span></a></li>\n"
        for pattern in patterns
    )
    sections = ""
    for heading, blocks in closing:
        sections += f"  <section>\n    <h2>{html.escape(heading, quote=False)}</h2>\n"
        sections += "".join(f"    {render_block(block, href)}\n" for block in blocks)
        sections += "  </section>\n"
    return (
        head(title, description, SECTION_URL, "website", data, icon)
        + top_nav(True)
        + f"""
<main class="wrap">
  <h1>{html.escape(title, quote=False)}</h1>
{opening}  <ol class="plist">
{items}  </ol>
{sections}  <p class="source"><a href="{BLOB}PATTERNS.md">Markdown source on GitHub</a></p>
</main>
"""
        + FOOT
    )


def build() -> dict[str, str]:
    """Every file under docs/patterns/, keyed by file name."""
    title, intro, patterns, closing = load(SOURCE.read_text(encoding="utf-8"))
    check_pins(patterns)
    tokens, icon = tour_look()
    href = link_resolver(patterns)

    outputs = {STYLESHEET: stylesheet(tokens)}
    outputs["index.html"] = index_page(title, intro, patterns, closing, href, icon)
    for i, pattern in enumerate(patterns):
        before = patterns[i - 1] if i else None
        after = patterns[i + 1] if i + 1 < len(patterns) else None
        outputs[pattern.page] = pattern_page(pattern, before, after, title, href, icon)
    return outputs


# ------------------------------------------------------------------- checks

VOID = {"meta", "link", "br", "hr", "img", "input"}


class PageAudit(HTMLParser):
    """Collect unbalanced tags and every reference a page makes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.open: list[str] = []
        self.errors: list[str] = []
        self.refs: list[str] = []
        self.h1 = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if tag not in VOID:
            self.open.append(tag)
        if tag == "h1":
            self.h1 += 1
        for key in ("href", "src"):
            if fields.get(key) is not None:
                self.refs.append(fields[key])
        if tag == "meta" and fields.get("property") in ("og:url", "og:image"):
            self.refs.append(fields.get("content") or "")

    def handle_endtag(self, tag: str) -> None:
        if not self.open or self.open[-1] != tag:
            line, _ = self.getpos()
            self.errors.append(f"line {line}: </{tag}> closes nothing open")
        else:
            self.open.pop()


def site_path(ref: str, page: str) -> str | None:
    """The file under docs/ that `ref` on `page` points at, or None if external."""
    if ref.startswith(SITE):
        path = ref[len(SITE) :]
    elif ABSOLUTE.match(ref):
        return None
    elif ref.startswith("#"):
        return f"patterns/{page}"
    else:
        path = posixpath.join("patterns", ref)
    path = path.partition("#")[0].partition("?")[0]
    if not path or path.endswith("/"):
        path += "index.html"
    return posixpath.normpath(path)


def audit(outputs: dict[str, str]) -> list[str]:
    """Problems in the built pages: bad nesting, or a link to nothing."""
    problems = []
    for name, content in outputs.items():
        if not name.endswith(".html"):
            continue
        rel = f"docs/patterns/{name}"
        page = PageAudit()
        page.feed(content)
        page.close()
        problems += [f"{rel}: {error}" for error in page.errors]
        if page.open:
            problems.append(f"{rel}: never closed: {', '.join(page.open)}")
        if page.h1 != 1:
            problems.append(f"{rel}: {page.h1} <h1> elements, expected one")
        for ref in page.refs:
            path = site_path(ref, name)
            if path is None:
                continue
            built = path.startswith("patterns/") and path[len("patterns/") :] in outputs
            if path.startswith("../") or not (built or (DOCS / path).is_file()):
                problems.append(f"{rel}: {ref!r} resolves to no file under docs/")
    return problems


def ignored_files(outputs: dict[str, str]) -> list[str]:
    """Generated files a .gitignore rule matches, which no commit would carry.

    The file would exist locally and pass every other check here, then be
    missing from the push. --no-index asks about the name alone, so the answer
    is the same before and after the file is tracked.
    """
    paths = [f"docs/patterns/{name}" for name in outputs]
    run = subprocess.run(
        ["git", "check-ignore", "--no-index", "--", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode not in (0, 1):
        return [f"git check-ignore could not run: {run.stderr.strip()}"]
    return [
        f"{path} matches a .gitignore rule, so git would not publish it. "
        "Pin a different file name in SLUGS."
        for path in run.stdout.split("\n")
        if path.strip()
    ]


def stale_files(outputs: dict[str, str]) -> list[str]:
    """Files under docs/patterns/ that differ from, or are missing from, a build."""
    problems = []
    for name, content in outputs.items():
        path = OUT / name
        if not path.exists():
            problems.append(f"docs/patterns/{name} does not exist")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"docs/patterns/{name} is out of date")
    if OUT.is_dir():
        for path in sorted(OUT.iterdir()):
            if path.name not in outputs:
                problems.append(f"docs/patterns/{path.name} is not a generated file")
    return problems


def sitemap_problems(outputs: dict[str, str]) -> list[str]:
    """Pages the sitemap misses, and pattern URLs it lists with no page."""
    listed = re.findall(r"<loc>(.*?)</loc>", SITEMAP.read_text(encoding="utf-8"))
    wanted = [SECTION_URL] + [
        f"{SECTION_URL}{name}"
        for name in sorted(outputs)
        if name.endswith(".html") and name != "index.html"
    ]
    problems = []
    missing = [url for url in wanted if url not in listed]
    if missing:
        today = date.today().isoformat()
        entries = "".join(
            f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n"
            "    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n"
            for url in missing
        )
        problems.append(
            f"docs/sitemap.xml does not list {len(missing)} generated page(s). Add:\n"
            + entries.rstrip("\n")
        )
    for url in listed:
        if url.startswith(SECTION_URL) and url not in wanted:
            problems.append(f"docs/sitemap.xml lists {url}, which is not generated")
    return problems


# ----------------------------------------------------------------- selftest

SAMPLE = """# Patterns

Opening sentence. Second sentence with [a doc](ADOPTION.md).

## Index

| # | Pattern |
|---|---|
| 1 | [First](#p1) |

<a id="p1"></a>

## 1. Pure roles, composed with project facts

**Problem.** One "quoted end." Then *more* text.

**Where it lives:** [`samples/roles/`](samples/roles/) and [Pattern 1](#p1).

## How they compose

Closing paragraph.

---

*Last verified against the repo structure on 2026-01-01.*
"""


def run_self_test() -> int:
    """Assert the renderer on the shapes the source actually contains."""
    failures: list[str] = []

    def expect(label: str, actual: object, expected: object) -> None:
        if actual != expected:
            failures.append(f"  {label}: {actual!r} != {expected!r}")

    def refuses(label: str, text: str) -> None:
        try:
            load(text)
        except SystemExit:
            return
        failures.append(f"  {label}: accepted, expected a refusal")

    title, intro, patterns, closing = load(SAMPLE)
    expect("title", title, "Patterns")
    expect("opening paragraphs", len(intro), 1)
    expect(
        "patterns",
        [p.heading for p in patterns],
        ["1. Pure roles, composed with project facts"],
    )
    expect("the index table is not a block", len(patterns[0].blocks), 2)
    expect("closing sections", closing, [("How they compose", ["Closing paragraph."])])
    expect("description", description_of(patterns[0]), 'One "quoted end."')

    href = link_resolver(patterns)
    page = patterns[0].page
    expect("pN fragment", href("#p1"), page)
    expect("heading fragment", href("#1-pure-roles-composed-with-project-facts"), page)
    expect("other fragment", href("#index"), f"{BLOB}PATTERNS.md#index")
    expect("directory", href("samples/roles/"), f"{BLOB}samples/roles")
    expect("file", href("ADOPTION.md"), f"{BLOB}ADOPTION.md")
    expect("absolute", href("https://example.com/x"), "https://example.com/x")

    expect(
        "label, link and code",
        render_block(patterns[0].blocks[1], href),
        '<p><strong class="k">Where it lives:</strong> '
        f'<a href="{BLOB}samples/roles"><code>samples/roles/</code></a>'
        f' and <a href="{page}">Pattern 1</a>.</p>',
    )
    expect(
        "escaping",
        render_inline("a < b & `<file>` then *soft* and **hard *both* ends**", href),
        "a &lt; b &amp; <code>&lt;file&gt;</code> then <em>soft</em>"
        " and <strong>hard <em>both</em> ends</strong>",
    )
    expect(
        "plain text",
        plain_text("the `.env` and *large* [E1](x.md)"),
        "the .env and large E1",
    )
    expect(
        "sentence, versions",
        first_sentence("At v0.1.0 it ran. Then not."),
        "At v0.1.0 it ran.",
    )
    expect(
        "sentence, only one", first_sentence("No terminator here"), "No terminator here"
    )
    expect(
        "slug",
        suggest_slug(3, "Make it loud (the dead-man's switch) — now"),
        "03-make-it-loud-the-dead-mans-switch-now",
    )
    expect("github anchor", heading_anchor("10. A skill — never"), "10-a-skill--never")
    expect("site path, tour", site_path("../", "index.html"), "index.html")
    expect("site path, section", site_path("./", page), "patterns/index.html")
    expect("site path, external", site_path("https://example.com/", page), None)

    try:
        render_inline("an *unclosed run", href)
    except SystemExit:
        pass
    else:
        failures.append("  unbalanced emphasis: rendered, expected a refusal")

    refuses("a list", SAMPLE.replace("Closing paragraph.", "- a list item"))
    refuses("a wrong anchor", SAMPLE.replace('id="p1"', 'id="p2"'))
    refuses("a missing anchor", SAMPLE.replace('<a id="p1"></a>\n', ""))
    refuses(
        "an unpinned pattern",
        SAMPLE.replace(
            "## How they",
            '<a id="p999"></a>\n\n## 999. New\n\n**Problem.** P.\n\n## How they',
        ),
    )
    refuses("text under the rule", SAMPLE + "\nA stray paragraph.\n")

    unbalanced = PageAudit()
    unbalanced.feed("<p><em>x</p>")
    expect("the audit sees bad nesting", len(unbalanced.errors), 1)

    if failures:
        print("self-test: FAIL", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("self-test: PASS (renderer, link resolver, parser refusals, page audit).")
    return 0


# --------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed pages match PATTERNS.md; do not write",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="assert the renderer against fixed cases; do not write",
    )
    args = parser.parse_args()

    if args.selftest:
        return run_self_test()

    outputs = build()
    broken = audit(outputs) + ignored_files(outputs)
    if broken:
        print("ERROR: the built pages are not publishable:", file=sys.stderr)
        print("\n".join(f"  {line}" for line in broken), file=sys.stderr)
        return 2

    pages = sum(name.endswith(".html") for name in outputs) - 1

    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, content in outputs.items():
            # newline="\n" keeps the bytes the same on every platform.
            with open(OUT / name, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        print(
            f"Wrote docs/patterns/ ({pages} pattern pages, index.html, {STYLESHEET})."
        )

    problems = stale_files(outputs) + sitemap_problems(outputs)
    if problems:
        if args.check:
            print("STALE: docs/patterns/ is behind its sources:", file=sys.stderr)
        else:
            print("ERROR: the pages are written, but:", file=sys.stderr)
        print("\n".join(f"  {line}" for line in problems), file=sys.stderr)
        if args.check:
            print(f"Run: python {ME}", file=sys.stderr)
        return 1

    if args.check:
        print(f"docs/patterns/ is current ({pages} pattern pages and the index).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
