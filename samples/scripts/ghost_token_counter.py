"""Ghost-token baseline counter for the agent workspace.

Measures approximate tokens loaded before any user input. Helps spot when
SessionStart context growth gets expensive.

**What counts as "ghost tokens":**
- User-global CLAUDE.md (`~/.claude/CLAUDE.md`)
- Workspace CLAUDE.md (`<workspace>/CLAUDE.md`)
- Memory index + all always-loaded memory files (excludes `episodes/`)
- Skill frontmatter descriptions (one line each — the full SKILL.md body is
  NOT always-loaded, only the CSO-style description surfaces in the picker)
- Subagent frontmatter descriptions (same)
- Scheduled-task frontmatter descriptions (same — these don't fire on
  session start but are listed)
- Hook command strings from `~/.claude/settings.json`

**What's excluded:** MCP tool descriptions (would require live server query),
project CONTEXT.md files (loaded lazily when Claude reads them), SKILL.md
body content (loaded only on invocation).

**Token approximation:** chars / 4 (standard industry estimate for English).
Not exact Claude tokenisation but stable for relative comparisons week-over-
week. For absolute accuracy, swap in `tiktoken` with `cl100k_base`.

Usage:
  python ghost_token_counter.py baseline [--verbose]
  python ghost_token_counter.py trend [--weeks N]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("<workspace>")
HOME = Path.home() / ".claude"
DB_PATH = ROOT / "scripts" / "_state" / "ghost_tokens.db"

# Approximation: 1 token ≈ 4 chars for English prose.
CHARS_PER_TOKEN = 4


def ensure_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ghost_token_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taken_at TEXT NOT NULL,
            total_chars INTEGER NOT NULL,
            total_tokens_approx INTEGER NOT NULL,
            breakdown TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def approx_tokens(chars: int) -> int:
    return chars // CHARS_PER_TOKEN


def read_file_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return 0


def extract_frontmatter_description(path: Path) -> str:
    """Return the `description:` field from a SKILL.md / agent.md frontmatter.
    Returns empty string if not found or file missing."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    # match "description:" line through its terminator (either a blank line, a new
    # frontmatter key, or end of frontmatter)
    desc_m = re.search(
        r"^description:\s*(.+?)(?=^\w[\w-]*:|\Z)",
        fm,
        re.DOTALL | re.MULTILINE,
    )
    if not desc_m:
        return ""
    return desc_m.group(1).strip()


def count_file(label: str, path: Path) -> dict:
    chars = read_file_chars(path)
    return {
        "label": label,
        "path": str(path),
        "chars": chars,
        "tokens_approx": approx_tokens(chars),
    }


def count_directory_markdown(
    label: str, directory: Path, exclude_subdirs: tuple[str, ...] = ()
) -> dict:
    """Sum chars across all .md files in a directory, excluding named subdirs."""
    if not directory.exists():
        return {
            "label": label,
            "path": str(directory),
            "chars": 0,
            "tokens_approx": 0,
            "files": 0,
        }
    total = 0
    count = 0
    for p in directory.rglob("*.md"):
        if any(ex in p.relative_to(directory).parts for ex in exclude_subdirs):
            continue
        total += read_file_chars(p)
        count += 1
    return {
        "label": label,
        "path": str(directory),
        "chars": total,
        "tokens_approx": approx_tokens(total),
        "files": count,
    }


def count_descriptions(
    label: str, directory: Path, skill_md_pattern: str = "*/SKILL.md"
) -> dict:
    """Sum chars of only the `description:` frontmatter field across SKILL.md
    / subagent files. This is what the runtime actually surfaces at session
    start, not the full file body."""
    if not directory.exists():
        return {
            "label": label,
            "path": str(directory),
            "chars": 0,
            "tokens_approx": 0,
            "entries": 0,
        }
    total = 0
    count = 0
    # Try SKILL.md pattern first; if no hits, try root .md files (for agents folder)
    matches = list(directory.glob(skill_md_pattern))
    if not matches:
        matches = [p for p in directory.glob("*.md") if p.name != "README.md"]
    for p in matches:
        desc = extract_frontmatter_description(p)
        total += len(desc)
        count += 1
    return {
        "label": label,
        "path": str(directory),
        "chars": total,
        "tokens_approx": approx_tokens(total),
        "entries": count,
    }


def count_hook_commands(label: str, settings_path: Path) -> dict:
    """Sum chars of all hook `command` strings in settings.json."""
    if not settings_path.exists():
        return {
            "label": label,
            "path": str(settings_path),
            "chars": 0,
            "tokens_approx": 0,
            "entries": 0,
        }
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "label": label,
            "path": str(settings_path),
            "chars": 0,
            "tokens_approx": 0,
            "entries": 0,
        }
    hooks = settings.get("hooks", {})
    total = 0
    count = 0
    for _event, matchers in hooks.items():
        if not isinstance(matchers, list):
            continue
        for m in matchers:
            for h in m.get("hooks", []):
                cmd = h.get("command", "")
                if isinstance(cmd, str):
                    total += len(cmd)
                    count += 1
    return {
        "label": label,
        "path": str(settings_path),
        "chars": total,
        "tokens_approx": approx_tokens(total),
        "entries": count,
    }


def collect_breakdown() -> list[dict]:
    memory_dir = HOME / "projects" / "F--Claude" / "memory"
    return [
        count_file("CLAUDE.md (user-global)", HOME / "CLAUDE.md"),
        count_file("CLAUDE.md (workspace)", ROOT / "CLAUDE.md"),
        count_directory_markdown(
            "Memory (always-loaded, excl. episodes/)",
            memory_dir,
            exclude_subdirs=("episodes",),
        ),
        count_descriptions(
            "Skill descriptions (CSO)",
            ROOT / ".claude" / "skills",
        ),
        count_descriptions(
            "Subagent descriptions",
            ROOT / ".claude" / "agents",
            skill_md_pattern="*.md",
        ),
        count_descriptions(
            "Scheduled-task descriptions",
            HOME / "scheduled-tasks",
        ),
        count_hook_commands(
            "Hook command strings",
            HOME / "settings.json",
        ),
    ]


def cmd_baseline(args: argparse.Namespace) -> int:
    breakdown = collect_breakdown()
    total_chars = sum(b["chars"] for b in breakdown)
    total_tokens = approx_tokens(total_chars)

    conn = ensure_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO ghost_token_baselines
            (taken_at, total_chars, total_tokens_approx, breakdown)
            VALUES (?, ?, ?, ?)""",
        (now_iso, total_chars, total_tokens, json.dumps(breakdown, ensure_ascii=False)),
    )
    conn.commit()

    print(f"Ghost-token baseline @ {now_iso}")
    print(f"Total chars:  {total_chars:>8,}")
    print(f"Approx tokens: {total_tokens:>8,}  (~{CHARS_PER_TOKEN} chars/token)")
    print()
    print("Breakdown:")
    for b in breakdown:
        tok = b["tokens_approx"]
        extra = ""
        if "files" in b:
            extra = f"  ({b['files']} files)"
        elif "entries" in b:
            extra = f"  ({b['entries']} entries)"
        print(f"  {b['label']:<42}  {tok:>6,} tokens{extra}")

    if args.verbose:
        print()
        print(json.dumps(breakdown, indent=2, ensure_ascii=False))
    return 0


def cmd_trend(args: argparse.Namespace) -> int:
    conn = ensure_db()
    weeks = max(1, args.weeks)
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
    rows = list(
        conn.execute(
            """SELECT taken_at, total_tokens_approx, total_chars
            FROM ghost_token_baselines
            WHERE taken_at >= ?
            ORDER BY taken_at DESC""",
            (cutoff,),
        )
    )
    if not rows:
        print(
            f"No baselines recorded in last {weeks} week(s). Run: python {Path(__file__).name} baseline"
        )
        return 0
    print(f"Ghost-token trend (last {weeks} week(s)):")
    print(f"  {'WHEN':<28}  {'TOKENS':>8}  {'CHARS':>10}")
    for taken_at, tokens, chars in rows:
        print(f"  {taken_at:<28}  {tokens:>8,}  {chars:>10,}")
    if len(rows) >= 2:
        newest_tok = rows[0][1]
        oldest_tok = rows[-1][1]
        delta = newest_tok - oldest_tok
        pct = (delta / oldest_tok * 100) if oldest_tok else 0
        sign = "+" if delta >= 0 else ""
        print(f"\nDelta over window: {sign}{delta:,} tokens ({sign}{pct:.1f}%)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_base = sub.add_parser("baseline", help="measure + log the current baseline")
    p_base.add_argument(
        "--verbose", action="store_true", help="print full breakdown JSON"
    )
    p_base.set_defaults(func=cmd_baseline)

    p_trend = sub.add_parser("trend", help="show recent baselines")
    p_trend.add_argument("--weeks", type=int, default=4)
    p_trend.set_defaults(func=cmd_trend)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
