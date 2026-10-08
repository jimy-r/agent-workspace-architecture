#!/usr/bin/env python3
"""Memory lint — detect stale pointers in memory files.

Walks the auto-memory directory (`~/.claude/projects/<workspace-id>/memory/`) plus
its `episodes/` subfolder. For each markdown file, checks that every referenced
file path actually exists on disk.

`last_verified:` is a REVIEW clock, not a link-check clock. A clean broken-link
scan is not a review, so the bump is gated behind an explicit `--reviewed`,
asserted by whoever actually re-read the memories. `--fix` never touches it.

Two clocks, two owners (2026-09-06). The vendor writes
`modified:` (ISO 8601) into any memory file that already has frontmatter, so it
carries WRITE-recency for free and no workspace tool should try to reproduce it.
`last_verified:` carries REVIEW-recency, which no vendor can infer: it means a
human or an agent re-read the claims and found them still true. A file can be
freshly `modified` and years out of review, so never read one as the other.
A missing `modified:` is not a gap - it only appears once the vendor has written
the file since v2.1.214. All 33 topic files carry frontmatter (verified
2026-09-06), which is the precondition for the vendor stamp; MEMORY.md is the
index and stays frontmatter-free by design.

The clock is only worth having if something reads it, so `--clock` reports it
(unstamped files, and stamps older than STALE_AFTER_DAYS) and `--reviewed`
prints the same report before bumping. A review found 15 of 33 topic files
carried no stamp at all, the fact-densest among them, because the only writer
was a flag nothing invoked.

Source drift (2026-10-07). `--reviewed` also writes a
`source_digest` key beside the stamp: a digest of what the memory's
`verify_by_checking` value points at, which is the first existing local path
it names, and the section only when the value is `path#Heading` or
`path § Heading` (heading words, a quoted phrase, or a section number such
as `§ 3`). `--clock`
then lists the memories whose source changed since the review, scoped
digests first and whole-file ("unscoped") changes in a separate, lower
group. Advisory: no exit code moves, and a memory with no key or no digest
behaves exactly as before.

Usage:
    python memory_lint.py             # report only; exit 0 clean, 2 problems
    python memory_lint.py --fix       # (no last_verified bump — see --reviewed)
    python memory_lint.py --clock     # REVIEW clock only (last_verified), never the
                                      #   vendor's `modified:` write stamp; no writes;
                                      #   exit 0 when every topic file is stamped and
                                      #   fresh, 2 when any is unstamped or stale
                                      #   (source-drift lines print first and never
                                      #   move the exit)
    python memory_lint.py --reviewed a.md b.md
                                      # print the clock, then on a clean link scan
                                      #   refresh last_verified on the NAMED topic
                                      #   files only: the ones the review actually
                                      #   cross-checked (2026-09-24)
                                      #   and set source_digest beside it (2026-10-07)
    python memory_lint.py --reviewed  # no names: refresh every topic file, with a
                                      #   WARN, because a bulk stamp ties the clock
    python memory_lint.py --notes     # append problems to tasks/To Do Notes.md
    python memory_lint.py --lessons   # separate mode: dead backticked paths in
                                       # tasks/lessons.md, report only, never fixed
    python memory_lint.py --selftest  # temp-fixture tests; exit 0 pass, 1 fail

Detection heuristics:
- Markdown inline links:  [text](path)
- Backtick-quoted paths:  `<workspace>/...`, `~/.claude/...`
- Relative paths resolved first against <workspace>/ then against the file's dir.
- URLs / anchors / email / bracketed placeholders are ignored.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/<workspace-id>/memory"))
WORKSPACE_ROOT = Path("<workspace>")
TODO_NOTES = WORKSPACE_ROOT / "tasks" / "To Do Notes.md"

LINK_RE = re.compile(r"\]\(([^)]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([A-Z]:[\\/][^`\s]+|~/[^`\s]+)`")
IGNORE_PREFIXES = ("http://", "https://", "mailto:", "#", "<", "@")
# `<Skill>`, `<role>`, etc. — template placeholders embedded mid-path. These are
# intentional in pointer memories ("read `~/.claude/scheduled-tasks/<Skill>/...`")
# and must not be flagged, or a clean --fix run is impossible.
PLACEHOLDER_RE = re.compile(r"<[^>]+>")

# Paths that are created at runtime (browser profiles, MCP logs, OAuth state
# dirs). Memory files name them intentionally even when they don't exist yet.
RUNTIME_PATHS = frozenset(
    {
        "<home>/claude-profile",
        "<home>\\claude-profile",
        "~/.google_workspace_mcp",
        "~/.google_workspace_mcp/logs",
        "~/.claude/google-auth",
    }
)

LESSONS_PATH = WORKSPACE_ROOT / "tasks" / "lessons.md"

# A memory read more than a quarter ago is a point-in-time snapshot nobody has
# re-checked. Matches the 90-day migration horizon lessons.md consolidation uses.
STALE_AFTER_DAYS = 90

LAST_VERIFIED_RE = re.compile(
    r"^[ \t]*last_verified:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE
)
# Looser twin, used to find and rewrite the stamp line (a trailing parenthetical
# after the date is still a stamp). Detection and substitution share it so a
# second bump on the same day cannot fall through and insert a duplicate.
STAMP_LINE_RE = re.compile(r"^([ \t]*)last_verified: \d{4}-\d{2}-\d{2}", re.MULTILINE)

# Source-drift stamp (2026-10-07). `--reviewed` also
# records a digest of what a memory's `verify_by_checking` value points at, in a
# `source_digest` key beside the stamp, and `--clock` lists the memories whose
# source no longer matches it. Staleness is a question about the data, not about
# the clock: the digest hashes content, never mtime and never an agent's own
# account of the file. Advisory only, no exit code moves.
# Pattern credit: vectorize-io/hindsight@9269b884 hindsight-api-slim/hindsight_api/engine/memory_engine.py:2001-2007 (staleness is a question about data); NevaMind-AI/memU@2c050bc9 src/memu/hosts/bridging/manifest.py:7-10 (content digest, not mtime)
# The key reads `scoped:<16 hex>` when the value names `path#Heading` or
# `path § Heading` (that section only) and `unscoped:<16 hex>` when it names a
# bare path (whole file). An anchor that matches no heading stamps unscoped with
# ` anchor-not-found` after the hex. The two are reported apart because
# whole-file change flags most memories.
DIGEST_KEY = "source_digest"
SOURCE_DIGEST_RE = re.compile(
    r"^([ \t]*)source_digest:[ \t]*(.*?)[ \t]*$", re.MULTILINE
)
DIGEST_VALUE_RE = re.compile(
    r"""^["']?(scoped|unscoped):([0-9a-f]{16})(?: anchor-not-found)?["']?$"""
)
# A `§` straight after the path opens the anchor, as in `PLAN.md § 6`,
# `CLAUDE.md § Task Management` or `NOTES.md § "Last revised"`, the
# shapes the live values use.
SECTION_MARK_RE = re.compile(r"[ \t]*" + chr(0xA7) + r"[ \t]*")
VERIFY_BY_RE = re.compile(r"^[ \t]*verify_by_checking:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
# A path starts at a drive letter, `~/`, or a word followed by a slash, never in
# the middle of another token, and runs to the first character that cannot be in
# one. Spaces stay in the run so `My Project/PLAN.md` resolves; the
# longest prefix that exists wins (resolve_source).
PATH_START_RE = re.compile(
    r"(?<![\w/\\.~:-])(?:[A-Za-z]:[\\/]|~[\\/]|[\w.][\w.\-]*[\\/])"
)
PATH_STOP_RE = re.compile(r"[`\"|*?<>\r\n]")
# A memory that points at a credential store is never read for a digest.
SECRET_NAME_RE = re.compile(
    r"^\.env($|\.)|\.(pem|key|pfx|p12|kdbx)$|^id_(rsa|dsa|ecdsa|ed25519)"
    r"|^credentials?(\.|$)|^secrets?\.",
    re.IGNORECASE,
)
DIGEST_MAX_BYTES = 2_000_000
MARKDOWN_SUFFIXES = (".md", ".markdown")
# A `verify_by_checking` value is read up to this many characters, so a runaway
# line cannot turn the path search into thousands of stat calls.
MAX_VALUE_CHARS = 800
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")

# lessons.md cites workspace-relative paths with no drive letter (`scripts/x.py`,
# `.claude/rules/y.md`), unlike the memory files' drive-absolute / ~-relative
# convention (BACKTICK_PATH_RE above). Broader, so also noisier: a bare
# domain-like span (`github.com/x/y`) is excluded to cut the obvious
# false-positive class.
LESSONS_PATH_RE = re.compile(
    r"`((?:[A-Z]:[\\/]|~/)[^`\s]+|[A-Za-z][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_.\-]+)+/?)`"
)
DOMAIN_TLD_RE = re.compile(
    r"^[A-Za-z0-9_.\-]+\.[a-z]{2,4}(?:\.[a-z]{2})?/", re.IGNORECASE
)


def expand(p: str, base: Path) -> Path:
    p = p.strip().rstrip("/").rstrip("\\")
    if p.startswith("~"):
        return Path(os.path.expanduser(p))
    if re.match(r"^[A-Z]:[\\/]", p) or p.startswith("/"):
        return Path(p)
    candidate = WORKSPACE_ROOT / p
    if candidate.exists():
        return candidate
    return base / p


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        return text
    return text[end + 5 :]


def lint_file(path: Path) -> list[tuple[str, str]]:
    problems: list[tuple[str, str]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    body = strip_frontmatter(text)

    for m in LINK_RE.finditer(body):
        target = m.group(1).split(" ")[0].strip()
        if not target or target.startswith(IGNORE_PREFIXES):
            continue
        if PLACEHOLDER_RE.search(target):
            continue
        abs_path = expand(target, path.parent)
        if not abs_path.exists():
            problems.append((path.name, f'broken link "{target}"'))

    for m in BACKTICK_PATH_RE.finditer(body):
        ref = m.group(1).strip()
        if ref in RUNTIME_PATHS:
            continue
        if PLACEHOLDER_RE.search(ref):
            continue
        abs_path = expand(ref, path.parent)
        if not abs_path.exists():
            problems.append((path.name, f"broken path `{ref}`"))

    return problems


def lint_lessons(path: Path | None = None) -> list[tuple[int, str]]:
    """Scan tasks/lessons.md for backticked workspace paths that no longer exist.

    Report only, never edits lessons.md. This is the gstack `learn` pattern
    (prune stale entries by checking every referenced path exists) applied to
    the lessons file, a sibling scan to lint_file's memory-folder coverage.
    Reuses expand()'s workspace-root-first resolution and the same
    RUNTIME_PATHS / PLACEHOLDER_RE exemptions as lint_file, over a wider path
    regex (LESSONS_PATH_RE) since lessons.md's own convention is
    workspace-relative backticked paths, not drive-absolute / ~-relative.

    Heuristic, not exhaustive: a path cited by a shorthand that doesn't start
    at a real workspace root (e.g. an abbreviated `docs/...` for
    `projects/docs/...`) reports as dead even though the fuller path
    exists — a legitimate prod for a human to tighten the citation, consistent
    with this tool's report-only, human-judged posture.
    """
    path = path or LESSONS_PATH
    problems: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return problems
    for i, line in enumerate(text.split("\n"), start=1):
        for m in LESSONS_PATH_RE.finditer(line):
            ref = m.group(1).strip()
            if not ref or ref in RUNTIME_PATHS:
                continue
            if PLACEHOLDER_RE.search(ref) or DOMAIN_TLD_RE.match(ref):
                continue
            abs_path = expand(ref, path.parent)
            if not abs_path.exists():
                problems.append((i, ref))
    return problems


def read_last_verified(path: Path) -> str | None:
    """The frontmatter review stamp, or None when the file carries none.

    Frontmatter only: a `last_verified` mentioned in prose is a citation, not a
    clock, and must not be read as one.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    front = text[: end + 1] if end > 0 else text
    m = LAST_VERIFIED_RE.search(front)
    return m.group(1) if m else None


def say(notes: list[str] | None, line: str) -> None:
    """Hand a report line to the caller's list, or print it when there is none."""
    if notes is None:
        print(line)
    else:
        notes.append(line)


def front_of(text: str) -> str | None:
    """The frontmatter block (every line newline-terminated), or None when the
    file has none or never closes it."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return text[: end + 1] if end > 0 else None


def parse_source_digest(front: str) -> tuple[str, str] | None:
    """(scope, 16 hex) from the `source_digest` line, or None when the file has
    none or the value is not one this tool wrote."""
    m = SOURCE_DIGEST_RE.search(front)
    v = DIGEST_VALUE_RE.match(m.group(2)) if m else None
    return (v.group(1), v.group(2)) if v else None


def verify_by_value(front: str) -> str:
    """The `verify_by_checking` value with its YAML quoting removed, or ''."""
    m = VERIFY_BY_RE.search(front)
    raw = m.group(1) if m else ""
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        try:
            return json.loads(raw)
        except ValueError:
            return raw[1:-1]
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def _norm(text: str) -> str:
    """Line endings and a byte-order mark never count as a change."""
    return text.lstrip(chr(0xFEFF)).replace("\r\n", "\n").replace("\r", "\n")


def _hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _slug(text: str) -> str:
    text = re.sub(r"[`*~]", "", unquote(text)).strip().lower()
    text = re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", text))
    return re.sub(r"-+", "-", text).strip("-")


def _forms(slug: str) -> tuple[str, str]:
    """A heading slug, and the same without a leading section number."""
    return slug, re.sub(r"^\d+(?:-\d+)*-", "", slug)


def section_of(text: str, anchor: str) -> str | None:
    """The markdown section `anchor` names, heading line down to the next
    heading of the same or a higher level, or None when no heading matches.
    An anchor that opens with a section number (`3`, `3.2`) matches the first
    heading that starts with exactly that number. Otherwise a heading matches
    on its slug (with or without its own leading number), or by being the one
    heading that starts with the anchor (two or more words, or the whole
    anchor). Prose trailing the anchor is dropped a word at a time, longest
    first, until a heading matches. Fenced code is not scanned."""
    lines = _norm(text).split("\n")
    heads: list[tuple[int, int, str, str]] = []
    fence = ""
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if not fence:
                fence = stripped[:3]
            elif stripped.startswith(fence):
                fence = ""
            continue
        m = None if fence else HEADING_RE.match(line)
        if m:
            title = re.sub(r"[ \t]+#+$", "", m.group(2))
            heads.append((i, len(m.group(1)), _slug(title), title))
    words = anchor.split()[:16]
    hit: list[tuple[int, int, str, str]] = []
    if words and re.fullmatch(r"\d+(?:\.\d+)*\.?", words[0]):
        number = re.escape(words[0].rstrip("."))
        hit = [h for h in heads if re.match(number + r"(?!\d|\.\d)", h[3])]
    for n in range(0 if hit else len(words), 0, -1):
        want = _slug(" ".join(words[:n]))
        if not want:
            continue
        hit = [h for h in heads if want in _forms(h[2])]
        if not hit and (n >= 2 or n == len(words)):
            starts = [
                h for h in heads if any(f.startswith(want + "-") for f in _forms(h[2]))
            ]
            hit = starts if len(starts) == 1 else []
        if hit:
            break
    if not hit:
        return None
    start, level = hit[0][:2]
    stop = next((h[0] for h in heads if h[0] > start and h[1] <= level), len(lines))
    return "\n".join(lines[start:stop]).rstrip("\n")


def resolve_source(value: str, base: Path) -> tuple[Path, str | None] | None:
    """(path, heading anchor or None) for the first local path `value` names
    that exists, or None. A path may hold spaces, so the longest prefix that
    exists wins. The anchor is a `#Heading` glued to the end of the path, or
    the text after a `§` that directly follows it: a quoted phrase, a section
    number, or heading words with whatever prose trails them."""
    value = value[:MAX_VALUE_CHARS]
    for m in list(PATH_START_RE.finditer(value))[:12]:
        stop = PATH_STOP_RE.search(value, m.start())
        span = value[m.start() : stop.start() if stop else len(value)]
        span = span[: MAX_VALUE_CHARS // 2]
        cuts = [
            i
            for i in range(len(span), 0, -1)
            if i == len(span) or span[i].isspace() or span[i] == "#"
        ]
        for i in cuts:
            for cand in dict.fromkeys((span[:i], span[:i].rstrip(".,;:)]'"))):
                if not cand.strip():
                    continue
                try:
                    path = expand(cand, base)
                    if not path.exists():
                        continue
                except (OSError, ValueError):
                    continue
                if i < len(span) and span[i] == "#" and not span[i - 1].isspace():
                    return path, (span[i + 1 :].strip() or None)
                tail = value[m.start() + len(cand) :]
                mark = SECTION_MARK_RE.match(tail)
                rest = tail[mark.end() :].strip() if mark else ""
                if rest.startswith('"'):
                    rest = rest[1:].split('"', 1)[0].strip()
                return path, (rest or None)
    return None


def source_digest(
    value: str, base: Path, want: str | None = None
) -> tuple[str, str, str, bool] | None:
    """(scope, 16 hex, label, missed) for what `value` points at, or None when
    it names no readable file: a directory, a credential store, a file over
    DIGEST_MAX_BYTES, or one that cannot be read. scope is "scoped" when the
    value carries an anchor (`path#Heading` or `path § Heading`) on a markdown
    file and that section exists, else "unscoped" (the whole file), with
    `missed` true when an anchor was named but no section matched it. `want`
    pins the scope a stored stamp used: "unscoped" ignores any anchor, and
    "scoped" answers ("nosection", "", label, False) when the section is
    gone."""
    found = resolve_source(value, base)
    if found is None:
        return None
    path, anchor = found
    try:
        if (
            not path.is_file()
            or SECRET_NAME_RE.search(path.name)
            or path.stat().st_size > DIGEST_MAX_BYTES
        ):
            return None
        text = path.read_bytes().decode("utf-8", "replace")
    except OSError:
        return None
    missed = False
    if want != "unscoped" and anchor and path.suffix.lower() in MARKDOWN_SUFFIXES:
        section = section_of(text, anchor)
        if section is not None:
            return "scoped", _hex(section), f"{path.name}#{anchor[:60]}", False
    if want == "scoped":
        return "nosection", "", path.name, False
    if want != "unscoped" and anchor:
        missed = True
    label = f"{path.name}; no heading matches '{anchor[:40]}'" if missed else path.name
    return "unscoped", _hex(_norm(text).rstrip("\n")), label, missed


def set_digest_line(front: str, value: str | None) -> str:
    """`front` with its source_digest line set to `value`, or removed when
    `value` is None. A new line goes straight under the last_verified stamp, at
    the same indent."""
    m = SOURCE_DIGEST_RE.search(front)
    if m:
        if value is None:
            end = m.end() + 1 if front[m.end() : m.end() + 1] == "\n" else m.end()
            return front[: m.start()] + front[end:]
        return (
            front[: m.start()] + f"{m.group(1)}{DIGEST_KEY}: {value}" + front[m.end() :]
        )
    stamp = STAMP_LINE_RE.search(front)
    if value is None or not stamp:
        return front
    eol = front.find("\n", stamp.end())
    eol = len(front) if eol < 0 else eol + 1
    return front[:eol] + f"{stamp.group(1)}{DIGEST_KEY}: {value}\n" + front[eol:]


def stamped_front(front: str, base: Path) -> tuple[str, str | None]:
    """`front`, the stamp already bumped, with its source_digest set from the
    `verify_by_checking` value, plus a one-line note when the digest moved.
    Reads the frontmatter text once, changes only the digest line, and
    re-parses the result before returning. Raises on anything unexpected, and
    the caller then stamps without a digest, as before."""
    found = source_digest(verify_by_value(front), base)
    want = found[:2] if found else None
    value = f"{found[0]}:{found[1]}" if found else None
    if found and found[3]:
        value += " anchor-not-found"
    out = set_digest_line(front, value)
    if (
        not STAMP_LINE_RE.search(out)
        or parse_source_digest(out) != want
        or set_digest_line(out, None) != set_digest_line(front, None)
    ):
        raise ValueError("the source_digest edit did not re-parse as planned")
    if parse_source_digest(front) == want:
        return out, None
    if found:
        return out, f"  source digest {value} ({found[2]})"
    return out, "  source digest removed (the value names no readable file)"


def source_drift(
    memory_dir: Path | None = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Topic files whose stamped source no longer matches: (scoped changes,
    unscoped changes), each a list of (file name, reason). A file with no
    source_digest is not looked at."""
    memory_dir = memory_dir or MEMORY_DIR
    changed: list[tuple[str, str]] = []
    unscoped: list[tuple[str, str]] = []
    for f in sorted(memory_dir.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            front = front_of(f.read_text(encoding="utf-8", errors="replace"))
            stamp = parse_source_digest(front) if front else None
            if stamp is None:
                continue
            now = source_digest(verify_by_value(front), memory_dir, want=stamp[0])
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN source drift: skipped {f.name}: {exc!r}")
            continue
        what = "section" if stamp[0] == "scoped" else "file"
        if now is None:
            why = "target missing or unreadable"
        elif now[0] == "nosection":
            why = f"section not found ({now[2]})"
        elif now[1] != stamp[1]:
            why = f"{what} changed ({now[2]})"
        else:
            continue
        (changed if stamp[0] == "scoped" else unscoped).append((f.name, why))
    return changed, unscoped


def source_drift_safe(memory_dir: Path | None = None):
    """source_drift(), or None with a loud line when it fails, so the age clock
    still prints exactly as it did."""
    try:
        return source_drift(memory_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN source drift unavailable, age clock only: {exc!r}")
        return None


def review_clock(
    memory_dir: Path | None = None, today: date | None = None
) -> list[tuple[str, str | None, int | None]]:
    """Every topic file's review age: (name, stamp or None, age in days or None).

    Skips MEMORY.md for the same reason refresh_last_verified() does: it is the
    index, not a topic file.
    """
    memory_dir = memory_dir or MEMORY_DIR
    today = today or date.today()
    rows: list[tuple[str, str | None, int | None]] = []
    for f in sorted(memory_dir.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        stamp = read_last_verified(f)
        age: int | None = None
        if stamp:
            try:
                age = (today - date.fromisoformat(stamp)).days
            except ValueError:
                stamp = None
        rows.append((f.name, stamp, age))
    return rows


def print_review_clock(
    rows: list[tuple[str, str | None, int | None]],
    drift: tuple[list[tuple[str, str]], list[tuple[str, str]]] | None = None,
) -> int:
    """Print source drift, then unstamped + stale files. Returns how many need
    a review by age; drift is advisory and is never counted."""
    unstamped = [n for n, s, _ in rows if s is None]
    stale = sorted(
        ((n, s, a) for n, s, a in rows if a is not None and a > STALE_AFTER_DAYS),
        key=lambda r: -(r[2] or 0),
    )
    print(
        f"Review clock — {len(rows)} topic file(s): "
        f"{len(rows) - len(unstamped)} stamped, {len(unstamped)} unstamped, "
        f"{len(stale)} older than {STALE_AFTER_DAYS}d"
    )
    titles = (
        "source changed since review",
        "source file changed (unscoped), lower priority",
    )
    for title, group in zip(titles, drift or ([], [])):
        if group:
            print(f"  {title}, {len(group)} (advisory):")
            for name, why in group:
                print(f"    - {name}: {why}")
    for name in unstamped:
        print(f"  - no last_verified: {name}")
    for name, stamp, age in stale:
        print(f"  - stale {age}d (last_verified {stamp}): {name}")
    return len(unstamped) + len(stale)


def refresh_last_verified(
    today: str,
    memory_dir: Path | None = None,
    only: set[str] | None = None,
    notes: list[str] | None = None,
) -> list[str]:
    """Bump the review clock. Callers must have --reviewed: this asserts a human
    re-read the memories, which a link scan cannot establish. `only` limits the
    bump to the named files, the ones a review actually cross-checked; stamping
    every file after a pass that checked three tied the rotation key
    (2026-09-24). The same edit sets `source_digest` from the
    `verify_by_checking` value (2026-10-07). `notes` collects its report
    lines, and a failure there stamps without a digest, as before."""
    updated: list[str] = []
    memory_dir = memory_dir or MEMORY_DIR
    # All topic files, not just reference_* — half-coverage fakes an audit
    # MEMORY.md is the index, not a topic file.
    for ref_file in memory_dir.glob("*.md"):
        if ref_file.name == "MEMORY.md":
            continue
        if only is not None and ref_file.name not in only:
            continue
        text = ref_file.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue  # nothing to hold the stamp; leave it for a human
        end = text.find("\n---\n", 4)
        if end < 0:
            continue  # unterminated frontmatter; don't guess where it ends
        # Frontmatter only. A `last_verified` in the body is a citation, and
        # rewriting it would corrupt prose instead of moving the clock.
        front, rest = text[: end + 1], text[end + 1 :]
        if STAMP_LINE_RE.search(front):
            new_front = STAMP_LINE_RE.sub(
                lambda m: f"{m.group(1)}last_verified: {today}", front, count=1
            )
        else:
            new_front = re.sub(
                r"^---\n", f"---\nlast_verified: {today}\n", front, count=1
            )
        # One read, one edit, one write: the digest rides in the same
        # frontmatter edit as the stamp and is re-parsed before and after.
        stamped = new_front
        try:
            new_front, note = stamped_front(stamped, memory_dir)
        except Exception as exc:  # noqa: BLE001
            new_front, note = stamped, None
            say(
                notes,
                f"  WARN source digest skipped for {ref_file.name}: {exc!r}; "
                "stamped without it",
            )
        if new_front != front:
            ref_file.write_text(new_front + rest, encoding="utf-8")
            if (
                new_front != stamped
                and ref_file.read_text(encoding="utf-8") != new_front + rest
            ):
                ref_file.write_text(stamped + rest, encoding="utf-8")
                note = None
                say(
                    notes,
                    f"  WARN source digest for {ref_file.name} did not "
                    "re-parse after the write; stamped without it",
                )
            updated.append(ref_file.name)
            if note:
                say(notes, f"{note}: {ref_file.name}")
    return updated


def append_to_todo_notes(problems: list[tuple[str, str]]) -> int:
    """Append a drift block to tasks/To Do Notes.md. Idempotent per (file, msg)."""
    if not TODO_NOTES.exists():
        return 0
    existing = TODO_NOTES.read_text(encoding="utf-8")
    new_lines: list[str] = []
    for name, msg in problems:
        marker = f"Memory drift — {name}: {msg}"
        if marker in existing:
            continue
        new_lines.append(f"- [ ] {marker}")
    if not new_lines:
        return 0
    today = date.today().isoformat()
    block = f"\n\n## Memory — drift detected {today}\n\n" + "\n".join(new_lines) + "\n"
    TODO_NOTES.write_text(existing + block, encoding="utf-8")
    return len(new_lines)


def run_selftest() -> int:
    import tempfile

    failures: list[str] = []
    today = date(2026, 9, 5)

    def check(name: str, cond: bool, detail: str = "") -> None:
        if not cond:
            failures.append(f"{name}{': ' + detail if detail else ''}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "reference_a.md").write_text(
            "---\nname: a\nlast_verified: 2026-01-01\nmetadata:\n"
            "  type: reference\n---\n\nbody, last_verified: 1999-01-01 in prose\n",
            encoding="utf-8",
        )
        (tmp / "project_b.md").write_text(
            "---\nname: b\nmetadata:\n  type: project\n---\n\nbody\n",
            encoding="utf-8",
        )
        (tmp / "feedback_c.md").write_text("no frontmatter at all\n", encoding="utf-8")
        (tmp / "MEMORY.md").write_text(
            "---\nlast_verified: 2020-01-01\n---\nindex\n", encoding="utf-8"
        )

        rows = review_clock(tmp, today)
        by = {n: (s, a) for n, s, a in rows}
        check("index excluded", "MEMORY.md" not in by, str(sorted(by)))
        check("topic files found", len(rows) == 3, str(len(rows)))
        check("stamp parsed", by.get("reference_a.md", (None, None))[0] == "2026-01-01")
        check(
            "age computed",
            by.get("reference_a.md", (None, None))[1] == 247,
            str(by.get("reference_a.md")),
        )
        check("unstamped file", by.get("project_b.md") == (None, None))
        check("no frontmatter", by.get("feedback_c.md") == (None, None))

        check("clock counts unstamped + stale", print_review_clock(rows) == 3)

        updated = refresh_last_verified(today.isoformat(), tmp)
        check(
            "only frontmatter files stamped",
            sorted(updated) == ["project_b.md", "reference_a.md"],
            str(sorted(updated)),
        )
        check(
            "existing stamp bumped",
            read_last_verified(tmp / "reference_a.md") == "2026-09-05",
        )
        check(
            "stamp inserted",
            read_last_verified(tmp / "project_b.md") == "2026-09-05",
        )
        check(
            "frontmatter survives insert",
            "name: b" in (tmp / "project_b.md").read_text(encoding="utf-8"),
        )
        check(
            "no frontmatter left alone",
            read_last_verified(tmp / "feedback_c.md") is None,
        )
        check(
            "index untouched",
            read_last_verified(tmp / "MEMORY.md") == "2020-01-01",
        )
        check(
            "second bump is a no-op",
            refresh_last_verified(today.isoformat(), tmp) == [],
        )
        check(
            "clock clears after bump",
            print_review_clock(review_clock(tmp, today)) == 1,
        )

        # Named --reviewed stamps only the files a review cross-checked.
        later = "2026-09-24"
        named = refresh_last_verified(later, tmp, only={"project_b.md"})
        check("named stamp touches only the named file", named == ["project_b.md"])
        check(
            "unnamed file keeps its old stamp",
            read_last_verified(tmp / "reference_a.md") == "2026-09-05",
        )
        check(
            "empty name set stamps nothing",
            refresh_last_verified(later, tmp, only=set()) == [],
        )

        # --reviewed with broken refs refuses LOUDLY and stamps nothing.
        import contextlib
        import io

        before = read_last_verified(tmp / "reference_a.md")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = apply_reviewed(["--reviewed", "reference_a.md"], 2, "2026-09-30", tmp)
        check("broken refs: --reviewed exits non-zero", rc == 2)
        check(
            "broken refs: prints 'not stamped: 2 broken ref(s)'",
            "not stamped: 2 broken ref(s)" in out.getvalue(),
            out.getvalue(),
        )
        check(
            "broken refs: nothing stamped",
            read_last_verified(tmp / "reference_a.md") == before,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            rc = apply_reviewed(["--reviewed", "reference_a.md"], 0, "2026-09-30", tmp)
        check(
            "clean scan: named --reviewed exits 0 and stamps",
            rc == 0 and read_last_verified(tmp / "reference_a.md") == "2026-09-30",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            rc = apply_reviewed(["--reviewed", "MEMORY.md"], 0, "2026-09-30", tmp)
        check("the index is refused as a stamp target", rc == 2)

        # A bad stamp must read as unstamped, never crash the clock.
        (tmp / "project_b.md").write_text(
            "---\nlast_verified: 2026-13-99\n---\nbody\n", encoding="utf-8"
        )
        bad = {n: s for n, s, _ in review_clock(tmp, today)}
        check("bad date treated as unstamped", bad.get("project_b.md") is None)

        # The default link scan must be unaffected by any of the above. The
        # fixture points HOME at the temp dir so the backticked `~/` paths
        # resolve inside it, one live and one dead.
        (tmp / "live.md").write_text("live\n", encoding="utf-8")
        (tmp / "reference_a.md").write_text(
            "---\nname: a\n---\n\nsee `~/live.md` and `~/nope/gone.md`\n",
            encoding="utf-8",
        )
        saved_home = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(tmp)
        try:
            problems = lint_file(tmp / "reference_a.md")
        finally:
            for k, v in saved_home.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        check("link scan finds the dead path", len(problems) == 1, str(problems))
        check(
            "link scan keeps the live path",
            problems and "gone.md" in problems[0][1],
            str(problems),
        )

    # Source-drift stamp: scoped and unscoped digests, advisory flags, re-stamp.
    with tempfile.TemporaryDirectory() as td:
        mem, src = Path(td) / "mem", Path(td) / "src"
        mem.mkdir()
        src.mkdir()
        doc = src / "plan.md"

        def plan(alpha: str = "v1", beta: str = "v1", sub: str = "v1") -> None:
            doc.write_text(
                f"# Plan\n\n## Alpha\nalpha {alpha}\n\n## Beta\nbeta {beta}\n\n"
                f"### Beta sub\nsub {sub}\n\n## Gamma\ngamma v1\n",
                encoding="utf-8",
            )

        def memo(name: str, value: str | None) -> None:
            key = f"verify_by_checking: {value}\n" if value else ""
            (mem / name).write_text(
                f"---\nname: {name}\nlast_verified: 2026-01-01\n{key}---\nbody\n",
                encoding="utf-8",
            )

        def drift() -> tuple[list[str], list[str]]:
            hi, lo = source_drift(mem)
            return sorted(n for n, _ in hi), sorted(n for n, _ in lo)

        def digest_of(name: str) -> tuple[str, str] | None:
            text = (mem / name).read_text(encoding="utf-8")
            return parse_source_digest(front_of(text) or "")

        plan()
        memo("scoped.md", f"{doc.as_posix()}#Beta")
        memo("whole.md", doc.as_posix())
        memo("gone.md", (src / "gone.md").as_posix())
        memo("prose.md", "ask the user about it")
        memo("nokey.md", None)
        plain = (mem / "nokey.md").read_text(encoding="utf-8")
        refresh_last_verified("2026-10-07", mem, notes=[])
        check(
            "digest: a #Heading value is scoped",
            (digest_of("scoped.md") or ("",))[0] == "scoped",
        )
        check(
            "digest: a bare path is unscoped",
            (digest_of("whole.md") or ("",))[0] == "unscoped",
        )
        check(
            "digest: no file, prose value or no key gives no digest",
            digest_of("gone.md") is None
            and digest_of("prose.md") is None
            and digest_of("nokey.md") is None,
        )
        check(
            "digest: a file with no key stamps exactly as before",
            (mem / "nokey.md").read_text(encoding="utf-8")
            == plain.replace("2026-01-01", "2026-10-07"),
        )
        check(
            "drift: nothing flagged right after a stamp",
            drift() == ([], []),
            str(drift()),
        )
        plan(alpha="v2")
        check(
            "drift: another section changing leaves a scoped digest alone",
            drift() == ([], ["whole.md"]),
            str(drift()),
        )
        plan(alpha="v2", sub="v2")
        check(
            "drift: a change inside the section flags it, whole-file apart",
            drift() == (["scoped.md"], ["whole.md"]),
            str(drift()),
        )
        doc.write_text("# Plan\n\n## Alpha\nalpha v1\n", encoding="utf-8")
        why = dict(source_drift(mem)[0]).get("scoped.md", "")
        check(
            "drift: a removed section reads as not found",
            "section not found" in why,
            why,
        )
        doc.unlink()
        hi, lo = source_drift(mem)
        check(
            "drift: a vanished target flags both groups",
            [n for n, _ in hi] == ["scoped.md"] and [n for n, _ in lo] == ["whole.md"],
            str((hi, lo)),
        )
        plan(beta="v2")
        check(
            "drift: scoped flag before the re-stamp",
            drift()[0] == ["scoped.md"],
            str(drift()),
        )
        refresh_last_verified("2026-10-07", mem, notes=[])
        check("drift: re-stamping clears the flags", drift() == ([], []), str(drift()))
        num, mark = src / "num.md", chr(0xA7)
        num.write_text(
            "# Doc\n\n## 3. Pricing\np v1\n\n## 4. Terms\nt v1\n", encoding="utf-8"
        )
        memo("mark_num.md", f"{num.as_posix()} {mark} 3 pricing")
        memo("mark_txt.md", f'{num.as_posix()} {mark} "Terms" table')
        memo("mark_none.md", f"{num.as_posix()} {mark} Nowhere")
        refresh_last_verified("2026-10-07", mem, notes=[])
        check(
            "digest: a § section number and a § quoted heading are scoped",
            all(
                (digest_of(n) or ("",))[0] == "scoped"
                for n in ("mark_num.md", "mark_txt.md")
            ),
        )
        check(
            "digest: a § anchor with no heading stamps unscoped and says so",
            (digest_of("mark_none.md") or ("",))[0] == "unscoped"
            and "anchor-not-found"
            in (mem / "mark_none.md").read_text(encoding="utf-8"),
        )
        num.write_text(
            "# Doc\n\n## 3. Pricing\np v2\n\n## 4. Terms\nt v1\n", encoding="utf-8"
        )
        check(
            "drift: a § section flags only its own section",
            drift() == (["mark_num.md"], ["mark_none.md"]),
            str(drift()),
        )
        plan(beta="v3")
        rows = review_clock(mem, today)
        with contextlib.redirect_stdout(io.StringIO()):
            bare = print_review_clock(rows)
            flagged = print_review_clock(rows, source_drift(mem))
        check(
            "drift: the clock's count ignores drift",
            bare == flagged,
            f"{bare} vs {flagged}",
        )

    print("memory_lint selftest")
    if failures:
        print(f"  FAILED ({len(failures)}):")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("  PASSED (clock parsing, age, index exclusion, bump/insert idempotence,")
    print("          named --reviewed, bad-date guard, unchanged link scan,")
    print("          source-drift digest: scoped, unscoped, flags, re-stamp).")
    return 0


def apply_reviewed(
    args: list[str], broken: int, today: str, memory_dir: Path | None = None
) -> int:
    """Stamp last_verified for a --reviewed run; returns the exit code.

    A review is only stamped on a clean link scan. With broken references the
    stamp is refused LOUDLY (exit 2) rather than skipped in silence, which is
    what the old in-branch call did (verifier pass, 2026-09-24).
    """
    memory_dir = memory_dir or MEMORY_DIR
    if broken:
        print(
            f"  not stamped: {broken} broken ref(s). Fix them, then re-run --reviewed."
        )
        return 2
    names = {Path(a).name for a in args if not a.startswith("-")}
    unknown = sorted(
        n for n in names if n == "MEMORY.md" or not (memory_dir / n).is_file()
    )
    if unknown:
        print(f"  not a topic file, nothing stamped: {', '.join(unknown)}")
        return 2
    print_review_clock(review_clock(memory_dir), source_drift_safe(memory_dir))
    if not names:
        print(
            "  WARN bulk stamp: every topic file gets today's date. Name the "
            "files the review cross-checked instead."
        )
    notes: list[str] = []
    updated = refresh_last_verified(today, memory_dir, only=names or None, notes=notes)
    for name in updated:
        print(f"  updated last_verified -> {today}: {name}")
    for line in notes:
        print(line)
    if not updated:
        print(f"  every named topic file already stamped {today}")
    return 0


def main() -> int:
    flags = set(sys.argv[1:])

    if "--selftest" in flags:
        return run_selftest()

    if "--clock" in flags:
        needing = print_review_clock(review_clock(), source_drift_safe())
        if needing:
            print(
                "Re-read the memories, then `--reviewed` to clear these. "
                "--fix does not bump the clock."
            )
            return 2
        return 0

    if "--lessons" in flags:
        problems = lint_lessons()
        print(f"Memory lint --lessons — checked {LESSONS_PATH}")
        if not problems:
            print("Clean — no dead references.")
            return 0
        print(f"{len(problems)} dead reference(s) (report only, never edited):")
        for line_no, ref in problems:
            print(f"  - line {line_no}: `{ref}`")
        return 2

    all_problems: list[tuple[str, str]] = []
    files = sorted(MEMORY_DIR.glob("**/*.md"))
    for f in files:
        all_problems.extend(lint_file(f))

    print(f"Memory lint — checked {len(files)} files under {MEMORY_DIR}")

    if not all_problems:
        print("Clean — no broken references.")
        if "--reviewed" in flags:
            return apply_reviewed(sys.argv[1:], 0, date.today().isoformat())
        elif "--fix" in flags:
            print(
                "  (--fix does not bump last_verified; use --reviewed after a review)"
            )
        return 0

    print(f"{len(all_problems)} problem(s):")
    for name, msg in all_problems:
        print(f"  - {name}: {msg}")
    if "--reviewed" in flags:
        apply_reviewed(sys.argv[1:], len(all_problems), date.today().isoformat())

    if "--notes" in flags:
        added = append_to_todo_notes(all_problems)
        if added:
            print(f"Appended {added} new drift item(s) to {TODO_NOTES}")
        else:
            print("No new drift items — all already tracked.")

    return 2


if __name__ == "__main__":
    sys.exit(main())
