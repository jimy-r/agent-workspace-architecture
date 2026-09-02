"""cache_write_scan.py - attribute a session's prompt-cache WRITES to their causes.

Usage:
  python scripts/cache_write_scan.py                       newest transcript for this workspace
  python scripts/cache_write_scan.py <session-id-prefix|path> [--ttl-minutes 60] [--top 12] [--json]
  python scripts/cache_write_scan.py --selftest

Reads a Claude Code transcript (.jsonl), dedupes assistant steps by message id, and records per
step: cache_creation / cache_read / input / output tokens, the model, the wall-clock gap since the
previous step, and the previous step's tool calls. A step whose cache write exceeds REWRITE_SHARE
of its context is a re-write. Each re-write is attributed to the first matching cause:

  session-start  first step of the transcript
  compaction     a compaction marker sits between the previous step and this one
  model-switch   the model differs from the previous step's model
  idle-gap       the gap since the previous step exceeds the cache TTL
  standing-edit  the previous step edited CLAUDE.md / .claude/rules / memory files
  other          none of the above (worth a look)

Why this exists: Pattern 18 once said a mid-session edit to an always-loaded file forces a full
cache re-write. A scan of a 199-step session showed the opposite (three such edits at 168k-397k
context, next step fully cached) and found the real drivers were resumes after the TTL lapsed, one
model switch, and compaction. This script makes that check repeatable: it prints every step that
followed a standing-file edit so the claim can be re-tested on any transcript.

Sentinel: CACHE_WRITE_SCAN_OK steps=<n> rewrites=<n> write_tokens=<n> gap=<pct> model=<pct>
          compaction=<pct> standing=<pct> start=<pct> other=<pct>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

REWRITE_SHARE = 0.20
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
STANDING_MARKERS = (
    "CLAUDE.md",
    "MEMORY.md",
    ".claude\\rules",
    ".claude/rules",
    "\\memory\\",
    "/memory/",
)
CAUSES = (
    "session-start",
    "compaction",
    "model-switch",
    "idle-gap",
    "standing-edit",
    "other",
)


def project_dir() -> Path:
    """Claude Code keeps transcripts under ~/.claude/projects/<cwd with separators as dashes>/."""
    cwd = Path.cwd().resolve()
    slug = str(cwd).replace(":", "-").replace("\\", "-").replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


def resolve_transcript(arg: str | None) -> Path:
    if arg:
        p = Path(arg)
        if p.exists():
            return p
        hits = sorted(
            project_dir().glob(f"{arg}*.jsonl"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if hits:
            return hits[0]
        sys.exit(f"cache_write_scan: no transcript matches {arg!r} in {project_dir()}")
    hits = sorted(
        project_dir().glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True
    )
    if not hits:
        sys.exit(f"cache_write_scan: no transcripts in {project_dir()}")
    return hits[0]


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_steps(path: Path):
    steps: "OrderedDict[str, dict]" = OrderedDict()
    compaction_lines = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("isCompactSummary") or d.get("type") == "summary":
                compaction_lines.append(n)
            if d.get("type") != "assistant":
                continue
            msg = d.get("message") or {}
            mid = msg.get("id") or f"line{n}"
            row = steps.setdefault(
                mid,
                {
                    "line": n,
                    "ts": parse_ts(d.get("timestamp")),
                    "model": msg.get("model") or "?",
                    "cc": 0,
                    "cr": 0,
                    "inp": 0,
                    "out": 0,
                    "tools": [],
                },
            )
            u = msg.get("usage") or {}
            row["cc"] = max(row["cc"], u.get("cache_creation_input_tokens") or 0)
            row["cr"] = max(row["cr"], u.get("cache_read_input_tokens") or 0)
            row["inp"] = max(row["inp"], u.get("input_tokens") or 0)
            row["out"] = max(row["out"], u.get("output_tokens") or 0)
            content = msg.get("content") or []
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        target = (
                            inp.get("file_path")
                            or inp.get("path")
                            or str(inp.get("command", ""))[:60]
                        )
                        row["tools"].append((c.get("name") or "?", target))
    return list(steps.values()), compaction_lines


def ctx(row) -> int:
    return row["cc"] + row["cr"] + row["inp"]


def standing_edits(row) -> list[str]:
    return [
        t
        for name, t in row["tools"]
        if name in EDIT_TOOLS and any(m in t for m in STANDING_MARKERS)
    ]


def attribute(steps, compaction_lines, ttl_minutes: float):
    out = []
    comp = sorted(compaction_lines)
    for i, row in enumerate(steps):
        prev = steps[i - 1] if i else None
        gap_min = None
        if prev and row["ts"] and prev["ts"]:
            gap_min = (row["ts"] - prev["ts"]).total_seconds() / 60.0
        rewrite = ctx(row) > 0 and row["cc"] > REWRITE_SHARE * ctx(row)
        cause = None
        if rewrite:
            if prev is None:
                cause = "session-start"
            elif any(prev["line"] < c < row["line"] for c in comp):
                cause = "compaction"
            elif prev["model"] != row["model"]:
                cause = "model-switch"
            elif gap_min is not None and gap_min > ttl_minutes:
                cause = "idle-gap"
            elif standing_edits(prev):
                cause = "standing-edit"
            else:
                cause = "other"
        out.append(
            {
                "i": i,
                "gap_min": gap_min,
                "rewrite": rewrite,
                "cause": cause,
                "prev_standing": standing_edits(prev) if prev else [],
            }
        )
    return out


def report(path: Path, steps, attrib, ttl_minutes: float, top: int, as_json: bool):
    total_cc = sum(r["cc"] for r in steps)
    total_cr = sum(r["cr"] for r in steps)
    rewrites = [a for a in attrib if a["rewrite"]]
    by_cause = {c: 0 for c in CAUSES}
    for a in rewrites:
        by_cause[a["cause"]] += steps[a["i"]]["cc"]
    rewrite_tokens = sum(by_cause.values())

    def share(c):
        return (by_cause[c] / total_cc * 100.0) if total_cc else 0.0

    summary = {
        "transcript": str(path),
        "steps": len(steps),
        "rewrites": len(rewrites),
        "cache_write_tokens": total_cc,
        "cache_read_tokens": total_cr,
        "rewrite_tokens": rewrite_tokens,
        "ttl_minutes": ttl_minutes,
        "share_by_cause_pct": {c: round(share(c), 1) for c in CAUSES},
        "standing_edit_followups": [
            {
                "step": a["i"],
                "edited": a["prev_standing"],
                "cc": steps[a["i"]]["cc"],
                "cr": steps[a["i"]]["cr"],
                "ctx": ctx(steps[a["i"]]),
                "rewrite": a["rewrite"],
            }
            for a in attrib
            if a["prev_standing"]
        ],
    }
    if as_json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"transcript: {path}")
        print(
            f"steps={len(steps)}  cache_write={total_cc:,}  cache_read={total_cr:,}  "
            f"write share={(total_cc / (total_cc + total_cr) * 100.0) if (total_cc + total_cr) else 0:.1f}%  ttl={ttl_minutes:g}m"
        )
        print(
            f"\n== Re-writes (cache write > {int(REWRITE_SHARE * 100)}% of context), top {top} by size =="
        )
        for a in sorted(rewrites, key=lambda a: steps[a["i"]]["cc"], reverse=True)[
            :top
        ]:
            r = steps[a["i"]]
            ts = r["ts"].astimezone().strftime("%m-%d %H:%M") if r["ts"] else "?"
            gap = f"{a['gap_min']:.0f}m" if a["gap_min"] is not None else "-"
            print(
                f"  step {a['i']:4d} {ts}  gap={gap:>6}  {a['cause']:<13} write={r['cc']:>8,} read={r['cr']:>8,} ctx={ctx(r):>8,}  {r['model']}"
            )
        print("\n== Cache-write tokens by cause ==")
        for c in CAUSES:
            print(f"  {c:<13} {by_cause[c]:>10,}  {share(c):5.1f}%")
        print(
            f"  {'(steady-state)':<13} {total_cc - rewrite_tokens:>10,}  {100.0 - (rewrite_tokens / total_cc * 100.0 if total_cc else 0):5.1f}%"
        )
        print("\n== Steps following a standing-file edit (the doctrine test) ==")
        if not summary["standing_edit_followups"]:
            print("  none in this session")
        for f in summary["standing_edit_followups"]:
            flag = "RE-WRITE" if f["rewrite"] else "cached"
            print(
                f"  step {f['step']:4d} {flag:<8} write={f['cc']:>8,} read={f['cr']:>8,} ctx={f['ctx']:>8,}  edited {f['edited']}"
            )
    print(
        f"CACHE_WRITE_SCAN_OK steps={len(steps)} rewrites={len(rewrites)} write_tokens={total_cc} "
        f"gap={share('idle-gap'):.0f} model={share('model-switch'):.0f} compaction={share('compaction'):.0f} "
        f"standing={share('standing-edit'):.0f} start={share('session-start'):.0f} other={share('other'):.0f}"
    )
    return summary


def _synthetic_transcript(path: Path):
    def line(kind, ts, model="m1", cc=0, cr=0, inp=0, tools=(), extra=None):
        content = [{"type": "text", "text": "x"}]
        for name, target in tools:
            content.append(
                {
                    "type": "tool_use",
                    "id": "t",
                    "name": name,
                    "input": {"file_path": target},
                }
            )
        d = {
            "type": kind,
            "timestamp": ts,
            "message": {
                "id": f"msg{ts}",
                "model": model,
                "content": content,
                "usage": {
                    "cache_creation_input_tokens": cc,
                    "cache_read_input_tokens": cr,
                    "input_tokens": inp,
                    "output_tokens": 10,
                },
            },
        }
        if extra:
            d.update(extra)
        return json.dumps(d)

    rows = [
        line("assistant", "2026-01-01T00:00:00Z", cc=40000, cr=0),  # session-start
        line("assistant", "2026-01-01T00:01:00Z", cc=500, cr=40000),
        line(
            "assistant",
            "2026-01-01T00:02:00Z",
            cc=500,
            cr=40500,
            tools=[("Edit", "<home>/.claude/projects/x/memory/MEMORY.md")],
        ),
        line(
            "assistant", "2026-01-01T00:03:00Z", cc=600, cr=41000
        ),  # cached after standing edit
        line("assistant", "2026-01-01T02:00:00Z", cc=41600, cr=0),  # idle-gap
        line(
            "assistant", "2026-01-01T02:01:00Z", cc=41600, cr=0, model="m2"
        ),  # model-switch
        json.dumps({"type": "summary", "isCompactSummary": True}),
        line(
            "assistant", "2026-01-01T02:02:00Z", cc=9000, cr=0, model="m2"
        ),  # compaction
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "synthetic.jsonl"
        _synthetic_transcript(p)
        steps, comp = load_steps(p)
        attrib = attribute(steps, comp, ttl_minutes=60)
        causes = [a["cause"] for a in attrib if a["rewrite"]]
        expect = ["session-start", "idle-gap", "model-switch", "compaction"]
        follow = [a for a in attrib if a["prev_standing"]]
        ok = (
            causes == expect
            and len(follow) == 1
            and not follow[0]["rewrite"]
            and len(steps) == 7
        )
        print(
            f"causes={causes} expected={expect}; standing follow-ups={len(follow)} rewrite={follow[0]['rewrite'] if follow else None}"
        )
        print(
            "CACHE_WRITE_SCAN_SELFTEST_OK" if ok else "CACHE_WRITE_SCAN_SELFTEST_FAIL"
        )
        return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "session",
        nargs="?",
        help="session-id prefix or transcript path (default: newest)",
    )
    ap.add_argument(
        "--ttl-minutes",
        type=float,
        default=60.0,
        help="prompt-cache TTL in minutes (60 for the 1h setting, 5 for the default)",
    )
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    path = resolve_transcript(args.session)
    steps, comp = load_steps(path)
    if not steps:
        sys.exit(f"cache_write_scan: no assistant steps in {path}")
    attrib = attribute(steps, comp, args.ttl_minutes)
    report(path, steps, attrib, args.ttl_minutes, args.top, args.json)
    return 0


if __name__ == "__main__":
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main())
