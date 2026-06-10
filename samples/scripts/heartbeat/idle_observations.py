"""
Generate cheap local observations for heartbeat idle cycles.

Runs only when heartbeat has no classification / question / action work
this cycle (HEARTBEAT.md Phase "Idle-cycle observations"). Pulls from
local data only — task queue, rejection log, staging folders, memory
file mtimes. No subagents, no web fetches, no research.

Design constraints:
    - Cap the open observation queue at 3 entries in To Do Notes §
      AI Upgrades tagged `[Idle Observation]`. If 3+ are already open,
      produce zero new observations.
    - Dedupe: if the same observation shape was logged in the last 30
      days (open OR closed), skip. Shape = the identifying string
      used in the observation's bullet; we match on substring.
    - Surface at most 1 new observation per cycle.

Usage:
    python idle_observations.py
        -> prints proposed observation (one line) or "no observation"
        -> exit 0 on success (including "no observation")
        -> exit 2 if queue cap reached (caller can log + skip)

    python -m heartbeat.idle_observations
        -> same

The heartbeat reads the output and decides whether to append to
`tasks/To Do Notes.md § AI Upgrades`. This script does NOT write to
task files — it only proposes. The heartbeat is the writer.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).resolve().parents[2]
TASKS_DIR = WORKSPACE / "tasks"
TO_DO_NOTES = TASKS_DIR / "To Do Notes.md"
REJECTIONS = TASKS_DIR / "HEARTBEAT_REJECTIONS.md"
REVIEWS = TASKS_DIR / "HEARTBEAT_REVIEWS.md"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "F--Claude" / "memory"
PERSONAL_PROJECTS = WORKSPACE / "Personal" / "General Projects"

OPEN_QUEUE_CAP = 3
DEDUPE_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Observation shapes + sources
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    shape: str  # short identifying fingerprint for dedupe
    bullet: str  # full markdown bullet to append


# ---- source: rejection patterns --------------------------------------------


def _recent_rejection_clusters() -> Observation | None:
    """3+ rejections in the last 30 days sharing a lesson substring."""
    if not REJECTIONS.exists():
        return None
    content = REJECTIONS.read_text(encoding="utf-8")

    # Parse blocks (same structure as check_rejections.py)
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    header_re = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s*$")
    for line in content.splitlines():
        m = header_re.match(line)
        if m:
            if current:
                blocks.append(current)
            current = {"date": m.group(1), "title": m.group(2), "body": ""}
        elif current is not None:
            current["body"] += line + "\n"
    if current:
        blocks.append(current)

    cutoff = date.today() - timedelta(days=DEDUPE_WINDOW_DAYS)
    recent: list[dict[str, str]] = []
    for b in blocks:
        try:
            bd = date.fromisoformat(b["date"])
        except ValueError:
            continue
        if bd >= cutoff:
            recent.append(b)

    # Cheap clustering: group by 4+ char words in the "Lesson for future attempts" line
    lesson_re = re.compile(r"\*\*Lesson for future attempts:\*\*\s*(.+)", re.IGNORECASE)
    keywords: dict[str, int] = {}
    for b in recent:
        m = lesson_re.search(b["body"])
        if not m:
            continue
        lesson = m.group(1).lower()
        for word in re.findall(r"[a-z]{5,}", lesson):
            keywords[word] = keywords.get(word, 0) + 1

    common = [(k, v) for k, v in keywords.items() if v >= 3]
    if not common:
        return None
    common.sort(key=lambda kv: -kv[1])
    kw, count = common[0]
    shape = f"rejection-cluster:{kw}"
    bullet = (
        f"- **[Idle Observation] {count} recent rejections share keyword "
        f"`{kw}`** *(added {date.today().isoformat()})* — review recent "
        f"blocks in `tasks/HEARTBEAT_REJECTIONS.md`; classifier heuristics "
        f"may need tightening around this pattern."
    )
    return Observation(shape=shape, bullet=bullet)


# ---- source: stale staging folders -----------------------------------------


def _stale_staging() -> Observation | None:
    """Any *_staging folder older than 10 days with no recent activity."""
    cutoff_days = 10
    now = datetime.now()
    candidates: list[tuple[Path, int]] = []

    search_roots = [
        WORKSPACE / "tasks",
        WORKSPACE / "example-project",
        PERSONAL_PROJECTS,
        WORKSPACE / "Personal",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.glob("**/*_staging"):
            if not path.is_dir():
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue
            age = (now - mtime).days
            if age >= cutoff_days:
                candidates.append((path, age))

    if not candidates:
        return None

    candidates.sort(key=lambda pa: -pa[1])
    path, age = candidates[0]
    rel = path.relative_to(WORKSPACE).as_posix()
    shape = f"stale-staging:{rel}"
    bullet = (
        f"- **[Idle Observation] Stale staging folder: `{rel}` ({age}d old)** "
        f"*(added {date.today().isoformat()})* — no activity for {age} days; "
        f"integrate, reject, or delete. Use `/review-queue` to find the source "
        f"task or clean up manually."
    )
    return Observation(shape=shape, bullet=bullet)


# ---- source: old reference memory ------------------------------------------


def _stale_reference_memory() -> Observation | None:
    """Any reference_*.md with last_verified > 60 days ago."""
    cutoff = date.today() - timedelta(days=60)
    oldest: tuple[Path, date] | None = None

    for mf in MEMORY_DIR.glob("reference_*.md"):
        try:
            text = mf.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"^last_verified:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        if not m:
            continue
        try:
            lv = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if lv < cutoff and (oldest is None or lv < oldest[1]):
            oldest = (mf, lv)

    if oldest is None:
        return None

    path, lv = oldest
    age_days = (date.today() - lv).days
    shape = f"stale-ref-memory:{path.name}"
    bullet = (
        f"- **[Idle Observation] Reference memory `{path.name}` "
        f"last_verified {age_days}d ago** *(added {date.today().isoformat()})* — "
        f"verify against current state and bump the frontmatter date, or "
        f"prune if the pointer is no longer useful."
    )
    return Observation(shape=shape, bullet=bullet)


# ---- source: review queue batching opportunity ------------------------------


def _review_queue_batching() -> Observation | None:
    """5+ pending reviews where 3+ share a prefix-keyword in the task slug."""
    if not REVIEWS.exists():
        return None
    content = REVIEWS.read_text(encoding="utf-8")
    try:
        body = content.split("## Active reviews", 1)[1]
    except IndexError:
        return None

    entry_re = re.compile(
        r"^\s*-\s+\d{4}-\d{2}-\d{2}\s*\|\s*(?:pending|reminded)\s*\|\s*([^|]+?)\s*\|",
        re.MULTILINE,
    )
    slugs = [m.group(1).strip() for m in entry_re.finditer(body)]
    if len(slugs) < 5:
        return None

    keywords: dict[str, int] = {}
    for slug in slugs:
        for word in re.findall(r"[a-z]{4,}", slug.lower()):
            keywords[word] = keywords.get(word, 0) + 1

    common = [(k, v) for k, v in keywords.items() if v >= 3]
    if not common:
        return None
    common.sort(key=lambda kv: -kv[1])
    kw, count = common[0]
    shape = f"queue-batch:{kw}"
    bullet = (
        f"- **[Idle Observation] Review queue has {count} items sharing keyword "
        f"`{kw}`** *(added {date.today().isoformat()})* — batch integration via "
        f"`/review-queue` may be faster than draining one-by-one."
    )
    return Observation(shape=shape, bullet=bullet)


# ---------------------------------------------------------------------------
# Gates: queue cap + dedupe
# ---------------------------------------------------------------------------


def _open_observation_count() -> int:
    """Count open '[Idle Observation]' bullets in To Do Notes § AI Upgrades."""
    if not TO_DO_NOTES.exists():
        return 0
    content = TO_DO_NOTES.read_text(encoding="utf-8")
    parts = re.split(r"^## ", content, flags=re.MULTILINE)
    for part in parts:
        if part.startswith("AI Upgrades"):
            # Count non-struck-through observation bullets
            bullets = re.findall(r"^-\s+(.+)$", part, flags=re.MULTILINE)
            open_obs = [
                b
                for b in bullets
                if "[Idle Observation]" in b and not b.startswith("~~")
            ]
            return len(open_obs)
    return 0


def _seen_recently(shape: str) -> bool:
    """True if this observation shape appears in To Do Notes within dedupe window."""
    if not TO_DO_NOTES.exists():
        return False
    content = TO_DO_NOTES.read_text(encoding="utf-8")
    # Shape fingerprint: match the identifying part of the bullet
    key = shape.split(":", 1)[-1]
    # Look for the key as a substring of any `[Idle Observation]` bullet
    # within the last DEDUPE_WINDOW_DAYS days (dates are embedded as
    # `(added YYYY-MM-DD)` suffixes).
    cutoff = date.today() - timedelta(days=DEDUPE_WINDOW_DAYS)
    for match in re.finditer(
        r"\[Idle Observation\][^\n]*?\(added (\d{4}-\d{2}-\d{2})\)[^\n]*",
        content,
    ):
        try:
            added = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if added < cutoff:
            continue
        line = match.group(0)
        if key in line:
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


OBSERVATION_SOURCES = [
    _recent_rejection_clusters,
    _stale_staging,
    _stale_reference_memory,
    _review_queue_batching,
]


def propose_observation() -> Observation | None:
    """Return the first non-deduped, non-capped observation, or None."""
    if _open_observation_count() >= OPEN_QUEUE_CAP:
        return None

    for source in OBSERVATION_SOURCES:
        try:
            obs = source()
        except Exception:  # noqa: BLE001 — observation sources should never crash heartbeat
            continue
        if obs is None:
            continue
        if _seen_recently(obs.shape):
            continue
        return obs

    return None


def main() -> int:
    if _open_observation_count() >= OPEN_QUEUE_CAP:
        print("no observation (queue cap reached)")
        return 2

    obs = propose_observation()
    if obs is None:
        print("no observation")
        return 0

    print(obs.bullet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
