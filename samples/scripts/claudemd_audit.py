"""claudemd_audit — inventory and health-check the workspace's CLAUDE.md files.

Native in-house equivalent of the "CLAUDE.md Management" plugin (built rather
than installed, to keep the always-loaded-context surface auditable). CLAUDE.md
files are loaded automatically by path, so each one is a standing ghost-token
cost and a standing correctness liability if it drifts. This surfaces the
mechanical signals; a human (or the audit agent) makes the judgement calls.

Checks:
  - Inventory: every CLAUDE.md (size, lines, age in days).
  - Stale: not modified in > STALE_DAYS days.
  - Large: over LARGE_LINES lines or LARGE_BYTES bytes (ghost-token cost when
    that path is active).
  - Broken @-imports: `@<path>` references that don't resolve (relative to the
    file's directory, or absolute). A broken import = missing context at load.
  - Cross-file duplication: substantial lines appearing verbatim in 2+ files
    (boilerplate-extraction candidates — trim to cut ghost tokens).

Usage:
  python claudemd_audit.py            # scan the workspace + the user-global CLAUDE.md
  python claudemd_audit.py --quiet    # only flags, skip the full inventory
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# Resolved from this file's location: samples/scripts/ -> samples/ -> workspace root.
ROOT = Path(__file__).resolve().parent.parent
USER_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
SKIP_PARTS = {"node_modules", ".venv", "renv", "dist", "build", "__pycache__"}

STALE_DAYS = 45
LARGE_LINES = 150
LARGE_BYTES = 8192
DUP_MIN_LEN = 40  # only consider substantial lines for duplication
DUP_MIN_FILES = 2


def find_files() -> list[Path]:
    files = []
    for p in ROOT.rglob("CLAUDE.md"):
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        files.append(p)
    if USER_CLAUDE_MD.exists():
        files.append(USER_CLAUDE_MD)
    return sorted(files)


def at_imports(text: str) -> list[str]:
    """Return @-import targets. Matches a leading-@ token that looks like a path
    (contains a slash or ends in .md), not an @mention of an agent."""
    out = []
    for m in re.finditer(r"(?:^|\s)@([A-Za-z0-9_./:\\-]+)", text):
        tok = m.group(1)
        if "/" in tok or "\\" in tok or tok.endswith(".md"):
            out.append(tok)
    return out


def resolve(base: Path, target: str) -> bool:
    t = target.replace("\\", "/")
    cand = Path(t)
    if cand.is_absolute():
        return cand.exists()
    return (base.parent / t).exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--quiet", action="store_true", help="Only flags, skip inventory")
    args = ap.parse_args()

    files = find_files()
    if not files:
        print("No CLAUDE.md files found.")
        return 0

    now = time.time()
    stale, large, broken = [], [], []
    line_index: dict[str, list[Path]] = defaultdict(list)
    inventory = []

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        st = f.stat()
        age_days = (now - st.st_mtime) / 86400
        n_lines = text.count("\n") + 1
        inventory.append((f, st.st_size, n_lines, age_days))

        if age_days > STALE_DAYS:
            stale.append((f, age_days))
        if n_lines > LARGE_LINES or st.st_size > LARGE_BYTES:
            large.append((f, n_lines, st.st_size))
        for imp in at_imports(text):
            if not resolve(f, imp):
                broken.append((f, imp))
        for raw in text.splitlines():
            line = raw.strip()
            if len(line) >= DUP_MIN_LEN and not line.startswith("#"):
                line_index[line].append(f)

    if not args.quiet:
        print(f"CLAUDE.md inventory ({len(files)} files)")
        print("=" * 64)
        for f, size, n_lines, age in sorted(inventory, key=lambda x: -x[3]):
            rel = (
                str(f)
                .replace(str(ROOT).replace("\\", "/") + "/", "")
                .replace(str(USER_CLAUDE_MD), "~/.claude/CLAUDE.md")
            )
            print(f"  {age:5.0f}d  {n_lines:4d}L  {size:6d}B  {rel}")
        print()

    dups = {
        line: fs for line, fs in line_index.items() if len(set(fs)) >= DUP_MIN_FILES
    }

    flagged = False
    if stale:
        flagged = True
        print(f"STALE (> {STALE_DAYS} days):")
        for f, age in sorted(stale, key=lambda x: -x[1]):
            print(f"  {age:.0f}d  {f}")
        print()
    if large:
        flagged = True
        print(f"LARGE (> {LARGE_LINES} lines or {LARGE_BYTES}B — ghost-token cost):")
        for f, n_lines, size in large:
            print(f"  {n_lines}L {size}B  {f}")
        print()
    if broken:
        flagged = True
        print("BROKEN @-imports (referenced file does not resolve):")
        for f, imp in broken:
            print(f"  {f}  ->  @{imp}")
        print()
    if dups:
        flagged = True
        print(
            f"CROSS-FILE DUPLICATION ({len(dups)} line(s) in {DUP_MIN_FILES}+ files — extract candidates):"
        )
        for line, fs in sorted(dups.items(), key=lambda kv: -len(set(kv[1])))[:10]:
            n = len(set(fs))
            preview = line[:70] + ("…" if len(line) > 70 else "")
            print(f"  x{n}  {preview!r}")
        print()

    if not flagged:
        print("No flags. All CLAUDE.md files within thresholds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
