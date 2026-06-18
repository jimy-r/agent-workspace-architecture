#!/usr/bin/env python3
"""wrap_drift_scan.py — read-only, PRINT-ONLY workspace drift surfacer.

Invoked at the end of a `wrap` close-out skill to surface workspace-wide drift
to the operator while they are still in-context. It prints a compact
"## Drift noticed" markdown block to stdout and EXITS 0 ALWAYS.

This is the worked example for the "loop selection" pattern (PATTERNS.md): a
task close-out is recurring and verifiable but judgment-heavy, so it lands in
the SURFACE bucket, not LOOP. The scan adds no autonomy. It widens the
operator's view at the moment workspace state changed, and the operator
actions whatever they choose. Surface, don't act.

LOAD-BEARING CONSTRAINTS (audited in --selftest and by inspection):
  - READ-ONLY / PRINT-ONLY. This script never writes, edits, creates, or
    deletes any file. No state file, no JSONL, no canonical edits. The only
    filesystem side effects are stat()/read() and a subprocess that runs an
    optional project-strategy surfacer in its own read-only mode.
  - EXIT 0 ALWAYS. A surfacer must never break the wrap host run. Every check
    is wrapped in try/except; a failure prints "- (could not check X: reason)"
    and the scan continues.
  - Each external dependency degrades gracefully if missing or changed.

Four grounded checks (each grounded against real workspace sources):
  1. Stale CONTEXT.md / PLAN.md project docs (mtime > --days, default 30).
  2. Strategy flags via an OPTIONAL project-strategy surfacer, if one is
     present in the scripts dir. Fired triggers, staleness, and open
     decision-flag counts are surfaced from its --json (read-only) output;
     a non-zero exit is never allowed to abort this script. If no surfacer
     exists, this check reports "(not configured)" and the scan continues.
  3. Backup staleness via an optional audit-checks backup-recency helper.
  4. Open-question staleness — 'Status: AWAITING RESPONSE' blocks in the
     task-coordination questions file, with any embedded stale-flag age.

Paths use the repo's generic placeholders (`<workspace>`); substitute your own.
Stdlib only. No third-party deps.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

# --- Paths (resolve relative to this file so CWD does not matter) ------------
# In a real setup this file lives at <workspace>/scripts/wrap_drift_scan.py, so
# the scripts dir is this file's parent and the workspace root is its grandparent.
_SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPTS_DIR.parent
# An OPTIONAL project-strategy surfacer. If your workspace has one (a read-only
# script that prints fired triggers / staleness / open decision flags as JSON),
# drop it here and this check lights up; otherwise the check degrades cleanly.
STRATEGY_SURFACER = _SCRIPTS_DIR / "strategy_guard.py"
TODO_QUESTIONS = WORKSPACE / "tasks" / "To Do Questions.md"

# Dirs excluded from the CONTEXT/PLAN glob. Lowercased path-part match.
_EXCLUDE_PARTS = {".git", "node_modules", "public"}

DEFAULT_STALE_DAYS = 30


# =============================================================================
# Check 1 — stale CONTEXT.md / PLAN.md project docs
# =============================================================================
def _is_excluded(path: Path) -> bool:
    """True if any path component is an excluded dir (covers a public mirror
    dir, plus .git and node_modules anywhere in the tree)."""
    parts = {p.lower() for p in path.parts}
    return bool(parts & _EXCLUDE_PARTS)


def find_stale_context_docs(
    root: Path, days: int, now: dt.datetime
) -> list[tuple[Path, int]]:
    """Return [(path, age_days)] for every CONTEXT.md / PLAN.md older than `days`,
    excluding .git, node_modules, and a public mirror dir. Sorted oldest first."""
    cutoff_seconds = days * 86400.0
    stale: list[tuple[Path, int]] = []
    for name in ("CONTEXT.md", "PLAN.md"):
        for path in root.rglob(name):
            if _is_excluded(path):
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            age_seconds = now.timestamp() - mtime
            if age_seconds > cutoff_seconds:
                stale.append((path, int(age_seconds // 86400)))
    stale.sort(key=lambda t: t[1], reverse=True)
    return stale


def render_stale_context(root: Path, days: int, now: dt.datetime) -> list[str]:
    out = ["### Stale CONTEXT/PLAN docs"]
    try:
        stale = find_stale_context_docs(root, days, now)
    except Exception as exc:  # noqa: BLE001 — surfacer must never raise
        out.append(f"- (could not check stale docs: {exc})")
        return out
    if not stale:
        out.append("- (clean)")
        return out
    for path, age in stale:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        out.append(f"- {rel} — {age}d old (> {days}d)")
    return out


# =============================================================================
# Check 2 — strategy flags via an OPTIONAL project-strategy surfacer
# =============================================================================
def render_strategy_flags() -> list[str]:
    out = ["### Strategy flags"]
    if not STRATEGY_SURFACER.exists():
        # No surfacer configured for this workspace — degrade cleanly, never error.
        out.append("- (not configured: no project-strategy surfacer present)")
        return out
    try:
        # --json runs the surfacer in its own read-only mode and exits 0.
        # We never depend on the return code here; if it is non-zero we still
        # try to parse stdout, then fall back to a graceful message.
        proc = subprocess.run(
            [sys.executable, str(STRATEGY_SURFACER), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        out.append(f"- (could not check strategy: surfacer unrunnable: {exc})")
        return out

    raw = proc.stdout or ""
    try:
        data = json.loads(raw)
    except Exception:
        # Fall back to a --check style run for a count rather than crashing.
        try:
            chk = subprocess.run(
                [sys.executable, str(STRATEGY_SURFACER), "--check"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            # A surfacer's --check may exit 1 when it has findings — that is a
            # SUCCESSFUL run for us, not an error. Surface the count.
            findings = [
                ln.strip().lstrip("! ").strip()
                for ln in (chk.stdout or "").splitlines()
                if ln.strip().startswith("!")
            ]
            if findings:
                out.append(
                    f"- {len(findings)} strategy finding(s) — run the strategy surfacer for detail"
                )
            else:
                out.append("- (clean)")
        except Exception as exc:  # noqa: BLE001
            out.append(f"- (could not check strategy: {exc})")
        return out

    # Parse a generic JSON shape (triggers / staleness / open decisions).
    flagged = False

    triggers = data.get("triggers") or []
    fired = [t for t in triggers if isinstance(t, dict) and t.get("fired")]
    for t in fired:
        flagged = True
        dates = ", ".join(t.get("dates") or [])
        label = t.get("trigger") or "(unnamed trigger)"
        datestr = f" [{dates}]" if dates else ""
        out.append(f"- trigger FIRED: {label}{datestr}")

    if data.get("stale"):
        flagged = True
        last = data.get("last_revised") or "?"
        age = data.get("days_since_revised")
        agestr = f" ({age}d ago)" if age is not None else ""
        thr = data.get("stale_threshold_days")
        thrstr = f", threshold {thr}d" if thr is not None else ""
        out.append(f"- strategy doc stale: last revised {last}{agestr}{thrstr}")

    open_decisions = data.get("open_decisions") or []
    if open_decisions:
        aging = [d for d in open_decisions if isinstance(d, dict) and d.get("aging")]
        agingstr = f", {len(aging)} aging" if aging else ""
        flagged = True
        out.append(f"- {len(open_decisions)} open decision-flag item(s){agingstr}")

    if not flagged:
        out.append("- (clean)")
    return out


# =============================================================================
# Check 3 — backup staleness via an optional audit-checks backup helper
# =============================================================================
def render_backup_staleness() -> list[str]:
    out = ["### Backup staleness"]
    try:
        # Import the grounded helper, if present. Add the scripts dir to path so
        # an `audit_checks` package resolves regardless of CWD.
        if str(_SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS_DIR))
        from audit_checks.run_all import check_backup_recency  # type: ignore
    except Exception as exc:  # noqa: BLE001
        out.append(f"- (could not check backups: helper unavailable: {exc})")
        return out
    try:
        result = check_backup_recency()
    except Exception as exc:  # noqa: BLE001
        out.append(f"- (could not check backups: {exc})")
        return out

    status = (result or {}).get("status", "?")
    evidence = (result or {}).get("evidence", "")
    if status == "PASS":
        out.append(f"- (clean) {evidence}")
    else:
        # WARN (no-log / >7d nudge) or FAIL (>30d) — surface both.
        out.append(f"- {status}: {evidence}")
    return out


# =============================================================================
# Check 4 — open-question staleness in the questions file
# =============================================================================
# A stale-flag inside a Status line looks like: "(stale — 52 days, flagged ...)".
_STALE_AGE_RE = re.compile(r"stale\s*[—-]\s*(\d+)\s*days", re.IGNORECASE)
# A block opens on a markdown H2 header; its Status line follows.
_H2_RE = re.compile(r"^##\s+(.*)$")
_STATUS_RE = re.compile(r"^Status:\s*(.*)$", re.IGNORECASE)


def parse_awaiting_questions(text: str) -> list[tuple[str, int | None]]:
    """Return [(title, stale_age_days_or_None)] for each block whose Status line
    contains 'AWAITING RESPONSE'. Stale age is parsed from an embedded
    '(stale — N days ...)' marker when present."""
    blocks: list[tuple[str, int | None]] = []
    current_title: str | None = None
    lines = text.splitlines()
    for line in lines:
        h2 = _H2_RE.match(line)
        if h2:
            current_title = h2.group(1).strip()
            continue
        st = _STATUS_RE.match(line.strip())
        if st and current_title is not None:
            status_val = st.group(1)
            if "AWAITING RESPONSE" in status_val.upper():
                m = _STALE_AGE_RE.search(status_val)
                age = int(m.group(1)) if m else None
                blocks.append((current_title, age))
            # Consume the title so a block without a fresh H2 is not double-counted.
            current_title = None
    return blocks


def render_open_questions() -> list[str]:
    out = ["### Open-question staleness"]
    if not TODO_QUESTIONS.exists():
        out.append(f"- (could not check questions: {TODO_QUESTIONS.name} missing)")
        return out
    try:
        text = TODO_QUESTIONS.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        out.append(f"- (could not check questions: {exc})")
        return out
    try:
        blocks = parse_awaiting_questions(text)
    except Exception as exc:  # noqa: BLE001
        out.append(f"- (could not check questions: {exc})")
        return out

    if not blocks:
        out.append("- (clean)")
        return out

    staled = [(t, a) for (t, a) in blocks if a is not None]
    out.append(
        f"- {len(blocks)} block(s) AWAITING RESPONSE ({len(staled)} stale-flagged)"
    )
    # Surface the stale-flagged ones, oldest first, capped for compactness.
    staled.sort(key=lambda t: t[1], reverse=True)  # type: ignore[arg-type]
    for title, age in staled[:8]:
        out.append(f"  - {title} — stale {age}d")
    if len(staled) > 8:
        out.append(f"  - (+{len(staled) - 8} more stale-flagged)")
    return out


# =============================================================================
# Top-level scan
# =============================================================================
def run_scan(root: Path, days: int, now: dt.datetime) -> str:
    sections: list[list[str]] = []
    # Each renderer is itself fully try/excepted internally, but wrap the call
    # so even an unexpected explosion cannot abort the scan.
    for fn in (
        lambda: render_stale_context(root, days, now),
        render_strategy_flags,
        render_backup_staleness,
        render_open_questions,
    ):
        try:
            sections.append(fn())
        except Exception as exc:  # noqa: BLE001
            sections.append(["### (check crashed)", f"- (could not check: {exc})"])

    lines = ["## Drift noticed", ""]
    for sec in sections:
        lines.extend(sec)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# =============================================================================
# Selftest — in-process, no shell-piping (brittle on Windows)
# =============================================================================
def run_selftest() -> int:
    import tempfile
    import os

    failures: list[str] = []

    # --- 1. Staleness detector flags the old file and not the new one. -------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj_old = tmp / "OldProj"
        proj_new = tmp / "NewProj"
        proj_old.mkdir()
        proj_new.mkdir()
        old_doc = proj_old / "CONTEXT.md"
        new_doc = proj_new / "CONTEXT.md"
        old_doc.write_text("# old\n", encoding="utf-8")
        new_doc.write_text("# new\n", encoding="utf-8")

        now = dt.datetime.now()
        old_ts = (now - dt.timedelta(days=90)).timestamp()
        new_ts = (now - dt.timedelta(days=1)).timestamp()
        os.utime(old_doc, (old_ts, old_ts))
        os.utime(new_doc, (new_ts, new_ts))

        stale = find_stale_context_docs(tmp, days=30, now=now)
        stale_paths = {p.resolve() for p, _ in stale}
        if old_doc.resolve() not in stale_paths:
            failures.append("staleness: old CONTEXT.md was NOT flagged")
        if new_doc.resolve() in stale_paths:
            failures.append("staleness: new CONTEXT.md WAS wrongly flagged")

        # --- 1b. Exclusion: a doc under an excluded dir must be skipped. -----
        pub = tmp / "public" / "MirrorProj"
        pub.mkdir(parents=True)
        pub_doc = pub / "CONTEXT.md"
        pub_doc.write_text("# mirror\n", encoding="utf-8")
        os.utime(pub_doc, (old_ts, old_ts))
        stale2 = find_stale_context_docs(tmp, days=30, now=now)
        if pub_doc.resolve() in {p.resolve() for p, _ in stale2}:
            failures.append("exclusion: public/ mirror doc was NOT excluded")

    # --- 2. Exit-0 handling even when the strategy surfacer returns exit 1. --
    # A surfacer's --check may return exit 1 when it has findings; our render
    # path uses --json (exit 0) but the fallback branch must treat a non-zero
    # return as SUCCESS-with-findings, never propagate it. Verify the renderer
    # returns lines and does not raise regardless of the surfacer's exit code.
    try:
        lines = render_strategy_flags()
        if not lines or lines[0] != "### Strategy flags":
            failures.append("strategy: renderer did not return a section")
    except SystemExit:
        failures.append("strategy: renderer raised SystemExit (must not)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"strategy: renderer raised {exc!r} (must degrade, not raise)")

    # --- 3. Missing source degrades rather than raises. ---------------------
    # Point the question parser at a non-existent file via a temporary swap.
    global TODO_QUESTIONS
    saved = TODO_QUESTIONS
    try:
        TODO_QUESTIONS = WORKSPACE / "tasks" / "__no_such_file__.md"
        lines = render_open_questions()
        if not any("could not check" in ln for ln in lines):
            failures.append("missing-source: did not degrade gracefully")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"missing-source: raised {exc!r} instead of degrading")
    finally:
        TODO_QUESTIONS = saved

    # --- 4. The AWAITING-RESPONSE parser works on a known fixture. -----------
    fixture = (
        "## Foo\n"
        "Status: AWAITING RESPONSE (stale — 52 days, flagged 2026-06-10)\n\n"
        "## Bar\n"
        "Status: DEFERRED\n\n"
        "## Baz\n"
        "Status: AWAITING RESPONSE\n"
    )
    parsed = parse_awaiting_questions(fixture)
    titles = {t for t, _ in parsed}
    if titles != {"Foo", "Baz"}:
        failures.append(f"question-parse: expected {{Foo, Baz}}, got {titles}")
    ages = dict(parsed)
    if ages.get("Foo") != 52:
        failures.append(
            f"question-parse: Foo stale age expected 52, got {ages.get('Foo')}"
        )
    if ages.get("Baz") is not None:
        failures.append(
            f"question-parse: Baz stale age expected None, got {ages.get('Baz')}"
        )

    # --- 5. Whole-scan smoke: run_scan must produce the heading and not raise.
    try:
        with tempfile.TemporaryDirectory() as td:
            blob = run_scan(Path(td), days=30, now=dt.datetime.now())
        if not blob.startswith("## Drift noticed"):
            failures.append("run_scan: missing '## Drift noticed' heading")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"run_scan: raised {exc!r}")

    print("wrap_drift_scan selftest")
    if failures:
        print(f"  FAILED ({len(failures)}):")
        for f in failures:
            print(f"   - {f}")
        # The live `scan` path must always exit 0; only this dev-tool selftest
        # is allowed to exit non-zero so a real regression is loud.
        return 1
    print("  PASSED (staleness flag, public/ exclusion, strategy exit-1 handling,")
    print("          missing-source degrade, question parse, whole-scan smoke).")
    return 0


# =============================================================================
# CLI
# =============================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wrap_drift_scan.py",
        description="Read-only, print-only workspace drift surfacer for the wrap skill.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help=f"staleness threshold in days for CONTEXT/PLAN docs (default {DEFAULT_STALE_DAYS})",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="run in-process self-tests (the only mode that may exit non-zero)",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    # Live scan. Anything that goes wrong here is caught and printed; the scan
    # always returns a block and we always exit 0.
    try:
        blob = run_scan(WORKSPACE, args.days, dt.datetime.now())
        sys.stdout.write(blob)
    except Exception as exc:  # noqa: BLE001 — last-resort guard; must not crash wrap
        print("## Drift noticed")
        print("")
        print(f"- (drift scan failed entirely: {exc})")
    return 0


if __name__ == "__main__":
    # UTF-8-safe stdout/stderr on a legacy-codepage console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    # The live path always exits 0; only --selftest may return non-zero.
    code = main()
    if "--selftest" in sys.argv:
        sys.exit(code)
    sys.exit(0)
