#!/usr/bin/env python3
"""
Ideation-spar log -- the measurement engine behind PATTERNS.md #13 (a divergent
critic for half-formed ideas, held to a sample).

An always-on critique aid is also an unmeasurable one: if a challenge fires on
every fork you lose the counterfactual (what the thinking would have been without
it). This log preserves the counterfactual two ways:
  1. `roll` deterministically holds out ~1 in 3 eligible forks (no lens fired),
     so fired-vs-held-out is comparable at review.
  2. every fired challenge is tagged by the HUMAN, not the model -- a model
     grading its own challenges inherits a measured self-preference bias -- as
     changed / considered / noise.

Primary metric = material + actionable rate among fired forks.
Kill metric    = noise (restatement) rate; critique-theatre is the failure mode
                 this exists to catch. Register and review it like any scaffold
                 (PATTERNS.md #11): beat baseline at the review date, or cut it.

Stdlib only. Append-only JSONL, UTF-8.

CLI:
  roll                                          -> prints FIRE or HOLD_OUT (no write)
  log --disposition fired|held_out
      [--context S] [--challenge S] [--tag T]   -> appends a fork, prints its id
  retag ID TAG                                  -> human verdict: changed|considered|noise
  report [--since YYYY-MM-DD]                    -> rates + kill check
  recent [--n 15]                               -> last N forks
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import uuid
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
LOG = WORKSPACE / "scripts" / "_state" / "ideation_spar_log.jsonl"

VALID_DISPOSITIONS = {"fired", "held_out"}
VALID_TAGS = {"pending", "changed", "considered", "noise"}
VERDICT_TAGS = {"changed", "considered", "noise"}
HOLDOUT_EVERY = 3  # hold out 1 in N eligible forks
KILL_NOISE_RATE = 0.60
KILL_MIN_RESOLVED = 8


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def append(record: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")


def read_all() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    with LOG.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def forks() -> list[dict]:
    """Latest state per fork id: start from the fork record, apply latest retag."""
    state: dict[str, dict] = {}
    for rec in read_all():
        fid = rec.get("id")
        if not fid:
            continue
        if rec.get("event") == "fork":
            state[fid] = dict(rec)
        elif rec.get("event") == "retag" and fid in state:
            state[fid]["tag"] = rec.get("tag")
    return list(state.values())


def cmd_roll(args: argparse.Namespace) -> int:
    eligible = sum(1 for r in read_all() if r.get("event") == "fork")
    # 0,1 -> FIRE ; 2 -> HOLD_OUT ; 3,4 -> FIRE ; 5 -> HOLD_OUT ...
    print("HOLD_OUT" if eligible % HOLDOUT_EVERY == HOLDOUT_EVERY - 1 else "FIRE")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    if args.disposition not in VALID_DISPOSITIONS:
        print(f"invalid disposition: {args.disposition}", file=sys.stderr)
        return 2
    if args.tag and args.tag not in VALID_TAGS:
        print(f"invalid tag: {args.tag} (valid: {sorted(VALID_TAGS)})", file=sys.stderr)
        return 2
    fid = uuid.uuid4().hex[:8]
    tag = "n/a" if args.disposition == "held_out" else (args.tag or "pending")
    append(
        {
            "event": "fork",
            "id": fid,
            "ts": now_iso(),
            "disposition": args.disposition,
            "context": args.context or "",
            "challenge": args.challenge or "",
            "tag": tag,
        }
    )
    print(fid)
    return 0


def cmd_retag(args: argparse.Namespace) -> int:
    if args.tag not in VERDICT_TAGS:
        print(
            f"invalid tag: {args.tag} (valid: {sorted(VERDICT_TAGS)})", file=sys.stderr
        )
        return 2
    ids = {r["id"] for r in read_all() if r.get("event") == "fork"}
    if args.id not in ids:
        print(f"unknown fork id: {args.id}", file=sys.stderr)
        return 2
    append({"event": "retag", "id": args.id, "ts": now_iso(), "tag": args.tag})
    print(f"retagged {args.id} -> {args.tag}")
    return 0


def _filter_since(items: list[dict], since: str | None) -> list[dict]:
    if not since:
        return items
    cut = dt.datetime.fromisoformat(since)
    return [r for r in items if dt.datetime.fromisoformat(r["ts"]) >= cut]


def cmd_report(args: argparse.Namespace) -> int:
    items = _filter_since(forks(), args.since)
    if not items:
        print("no forks logged yet")
        return 0
    fired = [r for r in items if r["disposition"] == "fired"]
    held = [r for r in items if r["disposition"] == "held_out"]
    counts = {t: sum(1 for r in fired if r["tag"] == t) for t in VALID_TAGS}
    resolved = counts["changed"] + counts["considered"] + counts["noise"]

    def pct(n: int) -> str:
        return f"{n / resolved * 100:.0f}%" if resolved else "  -"

    print("ideation-spar measurement report")
    print("-" * 52)
    print(f"  eligible forks : {len(items)}")
    print(f"  fired          : {len(fired)}   held_out : {len(held)}")
    print(f"  pending verdict: {counts['pending']}")
    print("  fired verdicts (human-tagged):")
    print(
        f"    changed    (changed the call)      : {counts['changed']:>3}  {pct(counts['changed'])}"
    )
    print(
        f"    considered (real, didn't change)   : {counts['considered']:>3}  {pct(counts['considered'])}"
    )
    print(
        f"    noise      (restatement/irrelevant): {counts['noise']:>3}  {pct(counts['noise'])}"
    )
    if resolved:
        material = counts["changed"] / resolved
        actionable = (counts["changed"] + counts["considered"]) / resolved
        noise = counts["noise"] / resolved
        print("-" * 52)
        print(f"  material rate   (changed)          : {material * 100:.0f}%")
        print(f"  actionable rate (changed+considered): {actionable * 100:.0f}%")
        print(f"  noise rate                          : {noise * 100:.0f}%")
        if resolved >= KILL_MIN_RESOLVED and noise > KILL_NOISE_RATE:
            print()
            print(
                f"  >>> KILL CANDIDATE: noise rate {noise * 100:.0f}% over {KILL_NOISE_RATE * 100:.0f}% "
                f"({resolved} resolved). Critique-theatre - cut it (PATTERNS.md #11)."
            )
    else:
        print("  (no fired forks resolved yet - tag them with `retag`)")
    print("-" * 52)
    print("  review: compare fired vs held_out decision quality at the review date.")
    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    items = sorted(forks(), key=lambda r: r["ts"], reverse=True)[: args.n]
    for r in items:
        ctx = (r.get("context") or "")[:48]
        print(f"{r['ts']}  {r['disposition']:<8} [{r['tag']:>10}] {r['id']}  {ctx}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "roll", help="print FIRE or HOLD_OUT for the next eligible fork"
    ).set_defaults(func=cmd_roll)

    pl = sub.add_parser("log", help="append a fork record")
    pl.add_argument("--disposition", required=True, choices=sorted(VALID_DISPOSITIONS))
    pl.add_argument("--context", help="one-line description of the ideation fork")
    pl.add_argument("--challenge", help="the challenge surfaced (fired only)")
    pl.add_argument(
        "--tag", choices=sorted(VALID_TAGS), help="initial tag (default pending)"
    )
    pl.set_defaults(func=cmd_log)

    pr = sub.add_parser("retag", help="human verdict on a fired challenge")
    pr.add_argument("id")
    pr.add_argument("tag", choices=sorted(VERDICT_TAGS))
    pr.set_defaults(func=cmd_retag)

    prep = sub.add_parser("report", help="rates + kill check")
    prep.add_argument("--since", help="ISO date - only count forks on/after")
    prep.set_defaults(func=cmd_report)

    prc = sub.add_parser("recent", help="last N forks")
    prc.add_argument("--n", type=int, default=15)
    prc.set_defaults(func=cmd_recent)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
