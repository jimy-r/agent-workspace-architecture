#!/usr/bin/env python3
"""Golden-set reasoning-regression harness (Tier C, 2026-06-18).

The measurement foundation: nothing else in the workspace trends ANSWER
accuracy over time. Health/token/ghost-token instruments trend *cost* and
*config* state; this trends whether the model still gets frozen, known-hard
prompts RIGHT. Each case is seeded from a real `tasks/lessons.md` failure --
a situation the workspace has already been burned by -- frozen as a
self-contained prompt with DETERMINISTIC checks.

Why deterministic checks and NOT LLM-as-judge: a judge model scoring a
worker model's answer carries its own error rate (the >50% judge-error
ceiling on hard reasoning tasks), so a regression in the worker is
indistinguishable from noise in the judge. Regex / path-existence / exact
-string checks have zero judge error -- a check either matches or it
doesn't. The trade is coverage (only mechanically-checkable failure modes
qualify) for trustworthiness (a drop is real).

Variance floor: each case runs K times (default 5) for a pass-RATE +/-
stddev, never a single scalar. One sample of a stochastic model says
nothing; the rate is the signal and the stddev is its honesty.

NOT gating. This is read-only trend + report. The audit's
`check_reasoning_regression` reads the latest history record and WARNs (never
FAILs) on a material drop. The replay (this script) is the heavy step run on
the audit's invocation; the check is the cheap report.

Usage:
  python scripts/reasoning_golden_run.py run [--cases DIR] [--k N] [--model M]
                                              [--limit M] [--ts ISO] [--dry]
                                              [--arm NAME] [--no-write]
  python scripts/reasoning_golden_run.py selftest
  --dry   evaluate every case's checks against an inline `dry_fixture` answer
          instead of calling Claude -- deterministic, free self-test of the
          check evaluators. Use to prove the machine before spending tokens.

History record (one JSON line appended to scripts/_state/reasoning_history.jsonl):
  {ts, model, k, n_cases, composite_pass_rate, stddev, per_case:{id:rate}, dry,
   calls_ok, calls_failed, arm, duration_s, per_case_duration_s:{id:seconds},
   arm_comparable_cases}

The schema is APPEND-ONLY: fields are added, never repurposed. Old records
carry none of the instrumentation fields below and stay readable;
`scripts/audit_checks/run_all.py::check_reasoning_regression` consumes only
{dry, invalid_reason, composite_pass_rate, stddev, n_cases, model} and is
unaffected by additions.

Arm/cost instrumentation (2026-08-12):
  arm       Which context configuration produced the record. Default
            "project-surface" = the normal workspace-loaded configuration
            (--add-dir <workspace>, cwd = workspace, so the project CLAUDE.md
            and .claude/rules load). A comparison arm that drops the project
            surface would be "project-surface-off". No arm is truly "bare":
            the user-global ~/.claude/CLAUDE.md loads in every cwd.
  duration_s / per_case_duration_s
            Wall seconds, summed per case across its K calls. The COST proxy:
            the call path is `claude --print` with no --output-format json, so
            stdout carries the answer text and no cost figure. Recording a
            fabricated dollar value would be worse than none, so duration is
            what is recorded. If the call path ever moves to
            --output-format json, add cost_usd from the CLI's own accounting.
  arm_comparable_cases
            Count of the cases in this run whose file sets
            `"arm_comparable": true` -- cases whose answer is expected to be
            sensitive to the workspace surface, so an arm-vs-arm comparison
            over them is meaningful. Absent field = false.

Sibling instruments: scripts/audit_checks/run_all.py (config assertions),
scripts/token_report.py (token history -- the JSONL pattern this mirrors),
scripts/health.py (workspace health composite). Owner: the upgrade-audit
(invokes `run` to refresh history before check_reasoning_regression reports).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Windows consoles AND piped/redirected runs default to cp1252, which cannot
# encode characters like U+2264 (<=) that appear verbatim in case notes -- so
# the free `--dry` self-test crashes on the first such print. Force stdout/stderr
# to UTF-8 (errors='replace' as a belt-and-braces floor) when the stream supports
# reconfigure (Python 3.7+).
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parents[1]
CASES_DIR = WORKSPACE / "tests" / "reasoning_golden" / "cases"
HISTORY = WORKSPACE / "scripts" / "_state" / "reasoning_history.jsonl"

# The exact headless invocation this workspace uses for scheduled/unattended
# Claude calls, lifted from run-scheduled-skill.ps1 (Invoke-DirectSkill):
#   claude --print --permission-mode acceptEdits --effort max --model <m>
#          --add-dir <workspace>
# acceptEdits is harmless here (we read answers, never write), but matching
# the live invocation means the harness measures the model as the workspace
# actually runs it. No --max-budget-usd: a golden run is a bounded batch the
# operator fired deliberately, not a runaway-prone scheduled cycle.
CLAUDE_TIMEOUT_S = 240

# Credential for the headless child. A bare `claude --print` inherits none, so
# every ad-hoc run of this harness 401'd and wrote an all-zero record that reads
# as a catastrophic reasoning regression -- it invalidated the 2026-07-11,
# 2026-08-07 and 2026-08-16 records and left the suite one valid measurement in
# its whole history. Resolved once per run, not per call: 445 PowerShell
# decrypts would be absurd, and the point of the preflight in cmd_run is to
# learn the credential is missing BEFORE making 445 doomed calls.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from durable_token import child_env  # noqa: E402

_CHILD_ENV: dict | None = None
_CHILD_ENV_OK = False
_CHILD_ENV_DETAIL = "not resolved"


def resolve_child_env() -> tuple[dict, bool, str]:
    """Resolve the child environment once and cache it."""
    global _CHILD_ENV, _CHILD_ENV_OK, _CHILD_ENV_DETAIL
    if _CHILD_ENV is None:
        _CHILD_ENV, _CHILD_ENV_OK, _CHILD_ENV_DETAIL = child_env()
    return _CHILD_ENV, _CHILD_ENV_OK, _CHILD_ENV_DETAIL


# The arm label for a run made with the workspace surface loaded -- i.e. the
# invocation above. Deliberately not called "bare": the user-global
# ~/.claude/CLAUDE.md loads regardless of cwd, so a true off-arm has to drop
# --add-dir AND run from a scratch cwd (see tests/reasoning_golden/README.md).
DEFAULT_ARM = "project-surface"


# ---------------------------------------------------------------------------
# Check evaluators. Each takes (answer_text, check_dict) and returns
# (passed: bool, note: str). A case PASSES a run iff EVERY check passes.
# All evaluators are pure + deterministic -- this is the whole point.
# ---------------------------------------------------------------------------

# A file-path-shaped token: forward- or back-slashed, with an extension or a
# trailing slash. Deliberately conservative -- we'd rather miss a weird path
# than false-positive on prose. Used by no_fabricated_path.
_PATH_TOKEN_RE = re.compile(
    r"""
    (?<![\w./\\])                      # not mid-token
    (?:[A-Za-z]:[\\/])?                # optional drive
    (?:[\w.\-]+[\\/])+                 # >=1 dir segment with a slash
    [\w.\-]+\.[A-Za-z0-9]{1,5}         # filename.ext
    """,
    re.VERBOSE,
)

# A `path:line` or backtick-wrapped path citation. Either a backticked token
# containing a slash, or a bare path with a :line suffix.
_CITATION_RE = re.compile(
    r"`[^`]*[\\/][^`]*`"  # backtick-wrapped path
    r"|(?:[A-Za-z]:[\\/])?(?:[\w.\-]+[\\/])+[\w.\-]+(?::\d+)",  # path:line
)


def _check_must_contain(answer: str, c: dict) -> tuple[bool, str]:
    pat = c["pattern"]
    ok = re.search(pat, answer, re.IGNORECASE | re.DOTALL) is not None
    return ok, f"must_contain /{pat}/ -> {'hit' if ok else 'MISS'}"


def _check_must_not_contain(answer: str, c: dict) -> tuple[bool, str]:
    pat = c["pattern"]
    hit = re.search(pat, answer, re.IGNORECASE | re.DOTALL) is not None
    return (
        not hit
    ), f"must_not_contain /{pat}/ -> {'PRESENT(fail)' if hit else 'absent'}"


def _check_exact_value(answer: str, c: dict) -> tuple[bool, str]:
    val = c["value"]
    ok = val in answer
    return ok, f"exact_value {val!r} -> {'present' if ok else 'MISSING'}"


def _check_must_cite_path(answer: str, c: dict) -> tuple[bool, str]:
    ok = _CITATION_RE.search(answer) is not None
    return ok, f"must_cite_path -> {'cited' if ok else 'NO CITATION'}"


def _check_uncertainty_tag(answer: str, c: dict) -> tuple[bool, str]:
    # Default hedge vocabulary if the case names no explicit pattern.
    pat = c.get(
        "pattern",
        r"\[unverified\]|\[unconfirmed\]|\bcannot\s+(?:confirm|verify)\b"
        r"|\b(?:unable to|can't|cannot)\s+(?:confirm|verify)\b"
        r"|\bI'm not (?:sure|certain)\b|\bneed(?:s)? (?:to )?verif\w+\b"
        r"|\bunverified\b|\bnot confirmed\b",
    )
    ok = re.search(pat, answer, re.IGNORECASE) is not None
    return ok, f"uncertainty_tag -> {'hedged' if ok else 'NO HEDGE'}"


def _check_no_fabricated_path(answer: str, c: dict) -> tuple[bool, str]:
    """Every file-path token the answer ASSERTS as existing must resolve.

    Conservative on two axes to avoid false failures: (1) only path-SHAPED
    tokens (slash + extension) are checked; bare filenames and prose are
    ignored; (2) a token is resolved both absolutely and relative to the
    workspace root. A case may whitelist tokens via `allow` (e.g. an
    illustrative path the prompt itself supplied) -- those are never flagged.
    """
    allow = set(c.get("allow", []))
    bad: list[str] = []
    seen: set[str] = set()
    for m in _PATH_TOKEN_RE.finditer(answer):
        tok = m.group(0).strip().rstrip(".,);:")
        if tok in seen or tok in allow:
            continue
        seen.add(tok)
        # Skip obvious non-filesystem shapes (URLs, version-ish tokens).
        if "://" in tok or tok.lower().startswith(("http", "www.")):
            continue
        norm = tok.replace("\\", "/")
        candidates = [Path(norm)]
        if not Path(norm).is_absolute():
            candidates.append(WORKSPACE / norm)
        if not any(p.exists() for p in candidates):
            bad.append(tok)
    if bad:
        return False, f"no_fabricated_path -> NONEXISTENT: {', '.join(bad[:5])}"
    return True, f"no_fabricated_path -> all {len(seen)} path token(s) resolve"


_EVALUATORS = {
    "must_contain": _check_must_contain,
    "must_not_contain": _check_must_not_contain,
    "exact_value": _check_exact_value,
    "must_cite_path": _check_must_cite_path,
    "uncertainty_tag": _check_uncertainty_tag,
    "no_fabricated_path": _check_no_fabricated_path,
}


def evaluate(answer: str, checks: list[dict]) -> tuple[bool, list[str]]:
    """Run every check against one answer. Returns (all_passed, notes).

    Fail-open at the CHECK level: an unknown check type or an evaluator that
    raises is recorded as a FAILED check with an error note, never an abort --
    a malformed case must not crash the batch.
    """
    notes: list[str] = []
    all_ok = True
    for c in checks:
        ctype = c.get("type", "<missing>")
        fn = _EVALUATORS.get(ctype)
        if fn is None:
            all_ok = False
            notes.append(f"{ctype} -> UNKNOWN CHECK TYPE (fail)")
            continue
        try:
            ok, note = fn(answer, c)
        except Exception as exc:  # noqa: BLE001 -- fail-open by design
            ok, note = False, f"{ctype} -> evaluator error: {exc}"
        all_ok = all_ok and ok
        notes.append(note)
    return all_ok, notes


# ---------------------------------------------------------------------------
# Case loading + the headless Claude call.
# ---------------------------------------------------------------------------


def load_cases(cases_dir: Path) -> list[dict]:
    cases = []
    for path in sorted(cases_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"  WARN: skipping unreadable case {path.name}: {exc}")
            continue
        data["_file"] = path.name
        cases.append(data)
    return cases


RETRY_ATTEMPTS = 3
RETRY_BACKOFF_S = (5, 15)

# Counted, not hidden. Retrying a flaky transport is correct; silently absorbing
# a systemic failure is not, so the run record carries these and a rising
# retry rate is itself the signal.
RETRY_STATS = {"retried": 0, "recovered": 0}

# Auth and budget failures are deterministic: the same call will fail the same
# way in five seconds. Only transport-shaped failures are worth another attempt.
_NO_RETRY_MARKERS = (
    "401",
    "oauth",
    "authenticat",
    "budget",
    "credit balance",
    "invalid api key",
)


def _worth_retrying(err: str) -> bool:
    low = err.lower()
    return not any(m in low for m in _NO_RETRY_MARKERS)


def call_claude(prompt: str, model: str) -> tuple[str, str | None]:
    """One headless Claude call, retried on transport-shaped failure.

    Fail-open: any failure (non-zero exit, timeout, OSError) returns
    ("", "<reason>") so the caller records the run as a miss with a note
    rather than aborting the batch.

    Why the retry (2026-08-24): the first clean full run lost 22 of 445 calls
    (4.9%) to exit 1 with an EMPTY stderr over four hours. Auth was fine -- 423
    calls on the same credential succeeded. Every lost call is scored as a miss,
    so the flakiness biases the composite DOWNWARD and understates reasoning
    quality on the exact number the 2026-09-18 scaffold reviews turn on.
    """
    last_out, last_err = "", "no attempt made"
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        last_out, last_err = _call_claude_once(prompt, model)
        if last_err is None:
            if attempt > 1:
                RETRY_STATS["recovered"] += 1
            return last_out, None
        if attempt == RETRY_ATTEMPTS or not _worth_retrying(last_err):
            return last_out, last_err
        RETRY_STATS["retried"] += 1
        time.sleep(RETRY_BACKOFF_S[min(attempt - 1, len(RETRY_BACKOFF_S) - 1)])
    return last_out, last_err


def _call_claude_once(prompt: str, model: str) -> tuple[str, str | None]:
    cmd = [
        "claude",
        "--print",
        "--permission-mode",
        "acceptEdits",
        "--effort",
        "max",
        "--model",
        model,
        "--add-dir",
        str(WORKSPACE),
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CLAUDE_TIMEOUT_S,
            cwd=str(WORKSPACE),
            env=resolve_child_env()[0],
        )
    except subprocess.TimeoutExpired:
        return "", f"timeout after {CLAUDE_TIMEOUT_S}s"
    except OSError as exc:
        return "", f"invocation error: {exc}"
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()[:200]
        return proc.stdout or "", f"exit {proc.returncode}: {err}"
    return proc.stdout or "", None


# ---------------------------------------------------------------------------
# The run.
# ---------------------------------------------------------------------------


def run_case(case: dict, k: int, model: str, dry: bool) -> dict:
    """Run one case K times. Returns a per-case result dict.

    Fail-open at the CASE level: an exception anywhere in here is caught by
    the caller, which records the case as rate 0.0 with an error note.
    """
    cid = case.get("id", case.get("_file", "<unknown>"))
    checks = case.get("checks", [])
    passes = 0
    calls_ok = 0
    calls_failed = 0
    elapsed = 0.0
    run_notes: list[str] = []

    if dry:
        # Deterministic self-test: evaluate checks against the case's own
        # fixture answer K times (the result is identical each time, but we
        # honour K so the record shape matches a real run).
        fixture = case.get("dry_fixture", "")
        for _ in range(k):
            t0 = time.perf_counter()
            ok, notes = evaluate(fixture, checks)
            elapsed += time.perf_counter() - t0
            passes += 1 if ok else 0
        # One representative note set (deterministic) is enough.
        _, notes = evaluate(fixture, checks)
        run_notes = notes
        if not fixture:
            run_notes = ["DRY: no dry_fixture in case (evaluated empty answer)"]
    else:
        prompt = case.get("prompt", "")
        for i in range(k):
            t0 = time.perf_counter()
            answer, err = call_claude(prompt, model)
            elapsed += time.perf_counter() - t0
            if err is not None:
                run_notes.append(f"run{i + 1}: CALL FAILED ({err}) -> miss")
                calls_failed += 1
                continue
            calls_ok += 1
            ok, notes = evaluate(answer, checks)
            passes += 1 if ok else 0
            if i == 0:  # keep the first run's check notes for the report
                run_notes = notes

    rate = passes / k if k else 0.0
    return {
        "id": cid,
        "rate": round(rate, 3),
        "passes": passes,
        "k": k,
        "notes": run_notes,
        "calls_ok": calls_ok,
        "calls_failed": calls_failed,
        # Transport flakiness stays visible. A retry that silently rescues a
        # systemic fault would hide the fault; a rising retried/recovered ratio
        # is the signal that something upstream is degrading.
        "calls_retried": RETRY_STATS["retried"],
        "calls_recovered_by_retry": RETRY_STATS["recovered"],
        "duration_s": round(elapsed, 4),
    }


def run_batch(
    cases: list[dict],
    k: int,
    model: str,
    dry: bool,
    arm: str = DEFAULT_ARM,
    ts: str | None = None,
) -> dict:
    """Replay every case and build the history record. Prints the run report.

    Returns the record instead of writing it, so a caller (cmd_run, selftest)
    decides whether it reaches disk.
    """
    mode = "DRY (no Claude calls)" if dry else f"REAL (model={model})"
    print(
        f"Golden-set reasoning run -- {mode}, arm={arm}, K={k}, {len(cases)} case(s)\n"
    )

    per_case: dict[str, float] = {}
    per_case_duration: dict[str, float] = {}
    rates: list[float] = []
    calls_ok_total = 0
    calls_failed_total = 0
    arm_comparable = 0
    for case in cases:
        cid = case.get("id", case.get("_file", "<unknown>"))
        if case.get("arm_comparable") is True:
            arm_comparable += 1
        try:
            result = run_case(case, k, model, dry)
        except Exception as exc:  # noqa: BLE001 -- case-level fail-open
            print(f"  {cid:<34}  ERROR  {exc}")
            per_case[cid] = 0.0
            per_case_duration[cid] = 0.0
            rates.append(0.0)
            continue
        per_case[result["id"]] = result["rate"]
        per_case_duration[result["id"]] = result["duration_s"]
        rates.append(result["rate"])
        calls_ok_total += result["calls_ok"]
        calls_failed_total += result["calls_failed"]
        bar = (
            "PASS"
            if result["rate"] == 1.0
            else ("FAIL" if result["rate"] == 0.0 else "MIXED")
        )
        print(
            f"  {result['id']:<34}  {result['rate']:>5.0%}  "
            f"({result['passes']}/{result['k']})  {bar}"
        )
        for note in result["notes"]:
            print(f"      - {note}")

    composite = round(statistics.fmean(rates), 3) if rates else 0.0
    stddev = round(statistics.pstdev(rates), 3) if len(rates) > 1 else 0.0
    total_duration = round(sum(per_case_duration.values()), 4)
    print(
        f"\ncomposite pass-rate {composite:.0%}  (stddev across cases {stddev:.3f}, "
        f"n={len(rates)})"
    )
    print(
        f"arm={arm}  duration {total_duration:.1f}s  "
        f"arm-comparable cases {arm_comparable}/{len(cases)}"
    )
    if arm != DEFAULT_ARM:
        # check_reasoning_regression compares the two latest real records with
        # no arm filter, so an off-arm record trends against a project-surface
        # one and any delta reads as a model regression.
        print(
            f"  NOTE: arm '{arm}' is not the default; a written record will be "
            "compared against the prior record regardless of arm"
        )

    # Stamp: prefer an explicit ts (lets the audit pin a deterministic stamp);
    # else stamp at write time. Avoid embedding a nondeterministic date in any
    # cached/keyed path -- this only goes into the record value.
    record = {
        "ts": ts or dt.datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "k": k,
        "n_cases": len(rates),
        "composite_pass_rate": composite,
        "stddev": stddev,
        "per_case": per_case,
        "dry": bool(dry),
        "calls_ok": calls_ok_total,
        "calls_failed": calls_failed_total,
        "arm": arm,
        "duration_s": total_duration,
        "per_case_duration_s": per_case_duration,
        "arm_comparable_cases": arm_comparable,
    }
    if not dry and calls_failed_total and not calls_ok_total:
        # Every headless call failed, so the zeros measure the outage, not the
        # model. check_reasoning_regression excludes records carrying this field.
        record["invalid_reason"] = (
            f"all {calls_failed_total} calls failed -- outage artefact, not a measurement"
        )
    return record


def cmd_run(args) -> int:
    cases = load_cases(args.cases)
    if not cases:
        print(f"no cases found in {args.cases}")
        return 1
    if args.limit:
        cases = cases[: args.limit]

    # Credential preflight. Without this the harness cheerfully makes every call,
    # gets 401 on all of them, and appends an all-zero composite that looks like a
    # total reasoning collapse. Three history records were corrupted that way.
    # A missing credential is an instrument fault, not a measurement, so refuse to
    # produce a number rather than produce a false one.
    if not args.dry:
        _, cred_ok, detail = resolve_child_env()
        if not cred_ok:
            print(f"ABORT  credential unavailable - {detail}")
            print(
                "       A run without a credential yields all-zero rates that read as"
            )
            print(
                "       a reasoning regression. Refusing to write a false measurement."
            )
            print("       Fix: powershell scripts/run-scheduled-skill.ps1 -SetToken")
            print("       Check: python scripts/durable_token.py status")
            return 1
        print(f"credential: {detail}")

    record = run_batch(cases, args.k, args.model, args.dry, args.arm, args.ts)
    if not args.no_write:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        print(f"appended record to {HISTORY.relative_to(WORKSPACE)}")
    else:
        print("(--no-write: record not persisted)")
    return 0


# ---------------------------------------------------------------------------
# Selftest: proves the instrumentation fields exist AND that adding them did
# not change what the audit's check_reasoning_regression reads. Free (dry
# fixtures, temp dirs, no Claude calls, never touches the real history).
# ---------------------------------------------------------------------------

_ST_CASES = [
    {
        "id": "st-arm-comparable",
        "arm_comparable": True,
        "prompt": "unused in dry mode",
        "checks": [{"type": "must_contain", "pattern": "workspace"}],
        "dry_fixture": "The answer cites the workspace rule.",
    },
    {
        "id": "st-no-arm-field",
        "prompt": "unused in dry mode",
        "checks": [{"type": "must_contain", "pattern": "workspace"}],
        "dry_fixture": "The answer cites the workspace rule.",
    },
    {
        "id": "st-arm-comparable-false",
        "arm_comparable": False,
        "prompt": "unused in dry mode",
        "checks": [{"type": "must_contain", "pattern": "no-such-token"}],
        "dry_fixture": "The answer cites the workspace rule.",
    },
]

_ST_OLD_SCHEMA_FALLBACK = [
    {
        "ts": "2026-01-01T00:00:00",
        "model": "opus",
        "k": 5,
        "n_cases": 2,
        "composite_pass_rate": 0.7,
        "stddev": 0.1,
        "per_case": {"a": 0.8, "b": 0.6},
        "dry": False,
    },
    {
        "ts": "2026-01-02T00:00:00",
        "model": "opus",
        "k": 5,
        "n_cases": 2,
        "composite_pass_rate": 0.7,
        "stddev": 0.1,
        "per_case": {"a": 0.8, "b": 0.6},
        "dry": False,
    },
]


def _load_run_all(workspace: Path):
    """Import the audit checks module with its WORKSPACE pointed at a temp tree."""
    import importlib.util

    src = WORKSPACE / "scripts" / "audit_checks" / "run_all.py"
    spec = importlib.util.spec_from_file_location("_golden_selftest_run_all", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.WORKSPACE = workspace
    return mod


def _old_history_lines() -> list[str]:
    if HISTORY.exists():
        lines = [
            ln for ln in HISTORY.read_text(encoding="utf-8").splitlines() if ln.strip()
        ]
        if lines:
            return lines[-6:]
    return [json.dumps(r) for r in _ST_OLD_SCHEMA_FALLBACK]


def cmd_selftest(args) -> int:
    failures: list[str] = []

    def expect(label: str, cond: bool, detail: str = "") -> None:
        print(
            f"  [{'ok ' if cond else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}"
        )
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cases_dir = tmp / "cases"
        cases_dir.mkdir()
        for c in _ST_CASES:
            (cases_dir / f"{c['id']}.json").write_text(json.dumps(c), encoding="utf-8")
        cases = load_cases(cases_dir)

        print("\n[1/3] record shape (default arm)")
        rec = run_batch(cases, k=2, model="opus", dry=True, ts="2026-01-01T00:00:00")
        for field in (
            "ts",
            "model",
            "k",
            "n_cases",
            "composite_pass_rate",
            "stddev",
            "per_case",
            "dry",
        ):
            expect(f"legacy field present: {field}", field in rec)
        expect(
            "arm defaults to project-surface",
            rec.get("arm") == DEFAULT_ARM,
            repr(rec.get("arm")),
        )
        expect("duration_s recorded", isinstance(rec.get("duration_s"), float))
        expect(
            "per_case_duration_s keys match per_case keys",
            set(rec.get("per_case_duration_s", {})) == set(rec.get("per_case", {})),
        )
        expect(
            "arm_comparable_cases counts only true (absent/false excluded)",
            rec.get("arm_comparable_cases") == 1,
            str(rec.get("arm_comparable_cases")),
        )
        expect(
            "per_case still maps id -> rate",
            rec["per_case"]
            == {
                "st-arm-comparable": 1.0,
                "st-arm-comparable-false": 0.0,
                "st-no-arm-field": 1.0,
            },
            json.dumps(rec["per_case"]),
        )
        expect(
            "composite still computed from rates", rec["composite_pass_rate"] == 0.667
        )

        print("\n[2/3] arm label passthrough")
        rec_off = run_batch(
            cases, k=1, model="opus", dry=True, arm="project-surface-off"
        )
        expect("arm passthrough", rec_off.get("arm") == "project-surface-off")

        print("\n[3/3] check_reasoning_regression parses old + new records")
        state = tmp / "scripts" / "_state"
        state.mkdir(parents=True)
        hist = state / "reasoning_history.jsonl"
        old_lines = _old_history_lines()
        hist.write_text("\n".join(old_lines) + "\n", encoding="utf-8")
        run_all = _load_run_all(tmp)
        before = run_all.check_reasoning_regression()
        expect(
            "baseline (old records only) parses",
            before["status"] in ("PASS", "WARN"),
            before["status"],
        )

        hist.write_text(
            "\n".join(old_lines) + "\n" + json.dumps(rec) + "\n", encoding="utf-8"
        )
        after_dry = run_all.check_reasoning_regression()
        # The check's evidence carries a file-age string that is not stable
        # across two reads of a just-written file: st_mtime can land a few
        # microseconds AHEAD of datetime.now(), and timedelta.days floors that
        # negative delta to -1. Cosmetic (it never moves the verdict), so
        # normalise the age out rather than compare against a coin flip.
        age_re = re.compile(r"history -?\d+d old")
        expect(
            "new-schema DRY record leaves the verdict identical",
            (after_dry["status"], age_re.sub("history Nd old", after_dry["evidence"]))
            == (before["status"], age_re.sub("history Nd old", before["evidence"])),
            f"{before['status']} -> {after_dry['status']}",
        )

        real = dict(rec, dry=False, composite_pass_rate=0.65, stddev=0.38, n_cases=89)
        hist.write_text(
            "\n".join(old_lines) + "\n" + json.dumps(real) + "\n", encoding="utf-8"
        )
        after_real = run_all.check_reasoning_regression()
        expect(
            "new-schema REAL record parses and trends",
            after_real["status"] in ("PASS", "WARN")
            and "65%" in after_real["evidence"],
            f"{after_real['status']}: {after_real['evidence'][:120]}",
        )

    print()
    if failures:
        print(f"SELFTEST FAILED ({len(failures)}): {'; '.join(failures)}")
        return 1
    print("SELFTEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="replay cases K times and record the result")
    p_run.add_argument("--cases", type=Path, default=CASES_DIR)
    p_run.add_argument(
        "--k", type=int, default=5, help="runs per case (variance floor)"
    )
    p_run.add_argument("--model", default="opus")
    p_run.add_argument(
        "--limit", type=int, default=0, help="cap number of cases (0=all)"
    )
    p_run.add_argument("--ts", help="ISO timestamp to stamp (default: now)")
    p_run.add_argument(
        "--dry", action="store_true", help="self-test checks on fixtures"
    )
    p_run.add_argument(
        "--no-write", action="store_true", help="do not append to history (e.g. dry CI)"
    )
    p_run.add_argument(
        "--arm",
        default=DEFAULT_ARM,
        help=(
            f"context-configuration label for this run (default {DEFAULT_ARM}; "
            "a run without the project surface is project-surface-off)"
        ),
    )
    sub.add_parser("selftest", help="prove the record shape + audit compatibility")
    args = parser.parse_args()
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
