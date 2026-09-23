"""Email rules engine — parser, validator, and matcher for Reference/email-rules.md.

The rules file is a markdown document containing fenced YAML blocks. Each rule
describes how an email from a particular sender should be handled (label, archive,
delete, keep_in_inbox) and which downstream consumers (bill-monitor, receipt-capture,
email-triage, morning-brief, tax-receipts) care about it.

Matching uses most-specific-wins: subject-narrowing beats exact-sender beats
domain-pattern beats name-substring. Ties fall back to document order.

Agents invoke this via CLI; see the argparse subcommands at the bottom. The library
functions can also be imported directly.

Usage:
    python email_rules.py validate
    python email_rules.py stats
    python email_rules.py match --from "noreply@rideshare.example" --subject "Your trip receipt"
    python email_rules.py match-batch messages.json
    python email_rules.py draft-rule --from "newsender@example.com" --subject "Promo"
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

RULES_FILE = Path(__file__).resolve().parent.parent / "Reference" / "email-rules.md"
VALID_CONSUMERS = {
    "bill-monitor",
    "bill-monitor-secondary",
    "receipt-capture",
    "email-triage",
    "morning-brief",
    "tax-receipts",
    "appointment-confirmation",
    "none",
}
VALID_ACTION_KEYS = {"label", "archive", "delete", "star", "mark_read", "keep_in_inbox"}
PLACEHOLDER_IDS = {"kebab-case-unique-id"}


@dataclass
class Rule:
    """A single parsed email rule. Most fields are optional because rules can
    identify senders by address OR regex pattern OR display-name substring."""

    id: str
    extends: str | None = None
    sender_address: str | None = None
    sender_pattern: str | None = None
    sender_name_contains: str | None = None
    subject_contains: str | None = None
    subject_pattern: str | None = None
    action: dict[str, Any] = field(default_factory=dict)
    consumers: list[str] = field(default_factory=list)
    retention: str | None = None
    unsubscribe: dict[str, Any] = field(default_factory=dict)
    transient: bool = False
    notes: str | None = None
    source_index: int = 0  # document order for tie-breaking


def parse_rules_file(path: Path = RULES_FILE) -> list[Rule]:
    """Parse the markdown rules file and return a list of fully-resolved Rule objects.

    The file has fenced ```yaml blocks; only blocks after the `## Rules` header are
    treated as live rules (the pre-header block is a schema example).

    `extends: <parent-id>` inheritance is applied — parent fields are copied first,
    then the child overrides per-field. Placeholder IDs are skipped.
    """
    text = path.read_text(encoding="utf-8")
    rules_section = _extract_rules_section(text)
    yaml_blocks = _extract_yaml_blocks(rules_section)

    raw_rules: list[dict[str, Any]] = []
    for block in yaml_blocks:
        parsed = yaml.safe_load(block)
        if not parsed:
            continue
        if not isinstance(parsed, list):
            raise ValueError(
                f"Expected list at YAML block; got {type(parsed).__name__}"
            )
        raw_rules.extend(parsed)

    raw_rules = [r for r in raw_rules if r.get("id") not in PLACEHOLDER_IDS]
    raw_rules = _expand_senders_list(raw_rules)
    by_id = {r["id"]: r for r in raw_rules}
    resolved = [_resolve_extends(r, by_id) for r in raw_rules]

    return [_dict_to_rule(r, idx) for idx, r in enumerate(resolved)]


def _expand_senders_list(raw_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand rules that use `senders: [addr1, addr2, ...]` into one rule per address.

    A shorthand that bundles multiple addresses under one rule. Each expanded rule
    gets `<original-id>-<local-part>` as its id.
    """
    out: list[dict[str, Any]] = []
    for r in raw_rules:
        senders = r.get("senders")
        if not senders:
            out.append(r)
            continue
        for addr in senders:
            local = str(addr).split("@", 1)[0]
            slug = re.sub(r"[^a-z0-9\-]+", "-", local.lower()).strip("-") or "x"
            expanded = {k: v for k, v in r.items() if k != "senders"}
            expanded["id"] = f"{r['id']}-{slug}"
            expanded["sender"] = {"address": addr}
            out.append(expanded)
    return out


def effective_action(action: dict[str, Any], phase: str = "future") -> dict[str, Any]:
    """Resolve the applicable action dict given a phase.

    Rules can specify `action: {future: {...}, historical: {...}}` to differentiate
    behaviour for new arrivals versus backfill. Triage operates on `future` by
    default; backfill tools pass `phase="historical"`.
    """
    if not isinstance(action, dict):
        return {}
    if "future" in action or "historical" in action:
        sub = (
            action.get(phase) or action.get("future") or action.get("historical") or {}
        )
        return sub if isinstance(sub, dict) else {}
    return action


def _extract_rules_section(text: str) -> str:
    """Return the portion of the file at or after the `## Rules` heading."""
    marker = re.search(r"^## Rules\b", text, flags=re.MULTILINE)
    if not marker:
        raise ValueError("Could not find '## Rules' heading in the rules file")
    return text[marker.start() :]


def _extract_yaml_blocks(text: str) -> list[str]:
    """Pull out the content of every ```yaml ... ``` fenced block."""
    pattern = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)
    return [m.group(1) for m in pattern.finditer(text)]


def _resolve_extends(
    rule: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Merge parent rule fields into child if `extends` is set. Child wins per-key."""
    parent_id = rule.get("extends")
    if not parent_id:
        return rule
    parent = by_id.get(parent_id)
    if parent is None:
        raise ValueError(
            f"Rule '{rule.get('id')}' extends unknown parent '{parent_id}'"
        )
    # `action` and `sender` are replaced wholesale when the child provides them —
    # merging them would produce a mixed future/historical + flat action bag, which
    # is never what the author intends. Other dict fields (unsubscribe) still merge.
    REPLACE_WHOLESALE = {"action", "sender", "subject"}
    merged: dict[str, Any] = {}
    for src in (parent, rule):
        for k, v in src.items():
            if k == "extends":
                continue
            if k in REPLACE_WHOLESALE:
                merged[k] = v
            elif isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
    merged["id"] = rule["id"]
    return merged


def _dict_to_rule(d: dict[str, Any], source_index: int) -> Rule:
    sender = d.get("sender") or {}
    subject = d.get("subject") or {}
    action = d.get("action") or {}
    unsub = d.get("unsubscribe") or {}
    consumers = d.get("consumers") or []
    if isinstance(consumers, str):
        consumers = [consumers]
    return Rule(
        id=d["id"],
        extends=d.get("extends"),
        sender_address=sender.get("address"),
        sender_pattern=sender.get("pattern"),
        sender_name_contains=sender.get("name_contains"),
        subject_contains=subject.get("contains"),
        subject_pattern=subject.get("pattern"),
        action=action,
        consumers=consumers,
        retention=d.get("retention"),
        unsubscribe=unsub,
        transient=bool(d.get("transient", False)),
        notes=d.get("notes"),
        source_index=source_index,
    )


def validate_rules(rules: list[Rule]) -> list[str]:
    """Return a list of human-readable error strings. Empty list = all valid."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for r in rules:
        if r.id in seen_ids:
            errors.append(f"[{r.id}] duplicate id")
        seen_ids.add(r.id)

        if not any((r.sender_address, r.sender_pattern, r.sender_name_contains)):
            errors.append(
                f"[{r.id}] no sender criteria (need address, pattern, or name_contains)"
            )

        if r.sender_pattern:
            try:
                re.compile(r.sender_pattern)
            except re.error as e:
                errors.append(f"[{r.id}] invalid sender.pattern regex: {e}")
        if r.subject_pattern:
            try:
                re.compile(r.subject_pattern)
            except re.error as e:
                errors.append(f"[{r.id}] invalid subject.pattern regex: {e}")

        if not r.action:
            errors.append(f"[{r.id}] no action specified")
        else:
            # Support split schema: action: {future: {...}, historical: {...}}
            split_keys = {"future", "historical"}
            if set(r.action.keys()) & split_keys:
                # Validate each phase separately; unknown top-level keys outside split are an error
                extra = set(r.action.keys()) - split_keys
                if extra:
                    errors.append(
                        f"[{r.id}] action mixes split-phase keys with flat keys: {sorted(extra)}"
                    )
                for phase in ("future", "historical"):
                    sub = r.action.get(phase)
                    if sub is None:
                        continue
                    if not isinstance(sub, dict):
                        errors.append(f"[{r.id}] action.{phase} is not a mapping")
                        continue
                    unknown = set(sub.keys()) - VALID_ACTION_KEYS
                    if unknown:
                        errors.append(
                            f"[{r.id}] action.{phase} unknown keys: {sorted(unknown)}"
                        )
                    if not any(
                        sub.get(k) for k in ("delete", "label", "keep_in_inbox")
                    ):
                        errors.append(f"[{r.id}] action.{phase} no terminal directive")
            else:
                unknown_keys = set(r.action.keys()) - VALID_ACTION_KEYS
                if unknown_keys:
                    errors.append(
                        f"[{r.id}] unknown action keys: {sorted(unknown_keys)}"
                    )
                has_terminal = any(
                    r.action.get(k) for k in ("delete", "label", "keep_in_inbox")
                )
                if not has_terminal:
                    errors.append(
                        f"[{r.id}] action has no terminal directive (delete / label / keep_in_inbox)"
                    )

        for c in r.consumers:
            if c not in VALID_CONSUMERS:
                errors.append(f"[{r.id}] unknown consumer: {c!r}")

    return errors


def specificity(rule: Rule) -> int:
    """Higher = more specific. Subject rules dominate sender-only rules."""
    score = 0
    if rule.subject_pattern:
        score += 100
    if rule.subject_contains:
        score += 80
    if rule.sender_address:
        score += 20
    if rule.sender_pattern:
        score += 5
    if rule.sender_name_contains:
        score += 2
    return score


_EMAIL_RE = re.compile(r"<([^>]+)>|([^\s<>]+@[^\s<>]+)")


def _extract_email_and_name(from_header: str) -> tuple[str, str]:
    """Return (email_lower, display_name) parsed from a From: header value."""
    if not from_header:
        return "", ""
    from_header = from_header.strip()
    m = _EMAIL_RE.search(from_header)
    email = ""
    if m:
        email = (m.group(1) or m.group(2) or "").strip().lower()
    name = from_header
    if m:
        name = from_header[: m.start()].strip().strip('"')
    return email, name


def match(message: dict[str, Any], rules: list[Rule]) -> Rule | None:
    """Return the most-specific matching Rule, or None if no rule matches.

    `message` must have `from` (string, e.g. 'Name <a@b.com>') and optionally `subject`.
    """
    from_header = message.get("from", "")
    email, name = _extract_email_and_name(from_header)
    subject = message.get("subject", "") or ""

    candidates: list[Rule] = []
    for r in rules:
        if not _sender_matches(r, email, name):
            continue
        if not _subject_matches(r, subject):
            continue
        candidates.append(r)

    if not candidates:
        return None

    candidates.sort(key=lambda r: (-specificity(r), r.source_index))
    return candidates[0]


def _sender_matches(r: Rule, email: str, name: str) -> bool:
    if r.sender_address and r.sender_address.lower() == email:
        return True
    if r.sender_pattern and re.search(r.sender_pattern, email, re.IGNORECASE):
        return True
    if (
        r.sender_name_contains
        and name
        and r.sender_name_contains.lower() in name.lower()
    ):
        return True
    return False


def _subject_matches(r: Rule, subject: str) -> bool:
    if r.subject_contains and r.subject_contains.lower() not in subject.lower():
        return False
    if r.subject_pattern and not re.search(r.subject_pattern, subject):
        return False
    return True


def match_batch(
    messages: list[dict[str, Any]], rules: list[Rule]
) -> list[dict[str, Any]]:
    """Match a batch; return a list of {message_id, matched_rule_id | None, action}."""
    out = []
    for m in messages:
        rule = match(m, rules)
        out.append(
            {
                "message_id": m.get("id") or m.get("message_id"),
                "from": m.get("from"),
                "subject": m.get("subject"),
                "matched_rule_id": rule.id if rule else None,
                "action": rule.action if rule else None,
                "consumers": rule.consumers if rule else [],
            }
        )
    return out


def draft_unknown_rule(
    message: dict[str, Any], suggested_label: str | None = None
) -> str:
    """Generate a YAML rule block draft for a message whose sender has no rule.

    The output is a proposal — user reviews it in To Do Questions.md and either
    accepts (pastes into email-rules.md) or edits first.
    """
    from_header = message.get("from", "")
    email, name = _extract_email_and_name(from_header)
    subject = message.get("subject", "") or ""

    sender_display = name or email or "unknown"
    rule_id = _propose_rule_id(email, name)
    domain = email.split("@", 1)[1] if "@" in email else ""

    label_guess = suggested_label or _guess_label(email, domain, subject)
    if label_guess:
        action_line = f'{{label: "{label_guess}", archive: true}}'
    else:
        action_line = '{label: "TBD", archive: true}'

    block = f"""- id: {rule_id}
  sender: {{address: "{email}"}}
  action: {action_line}
  consumers: [email-triage]
  retention: 1 year
  notes: >
    AUTO-PROPOSED 2026-04-19 from unknown sender "{sender_display}".
    Sample subject: "{subject[:80]}".
    REVIEW BEFORE APPLYING. Adjust label, consumers, retention as needed.
"""
    return block


def _propose_rule_id(email: str, name: str) -> str:
    """Generate a kebab-case id from sender email/name."""
    source = email or name or "unknown-sender"
    source = source.replace("@", "-").replace(".", "-")
    slug = re.sub(r"[^a-z0-9\-]+", "-", source.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:60] or "unknown-sender"


def _guess_label(email: str, domain: str, subject: str) -> str | None:
    """Light heuristics for a starter label guess — user must confirm."""
    s = subject.lower()
    if any(k in s for k in ("receipt", "invoice", "tax invoice", "your order")):
        return "Financial/Receipts/Shopping"
    if any(k in s for k in ("bill", "statement", "amount due", "payment due")):
        return "Financial/Receipts/Bills"
    if any(k in s for k in ("appointment", "booking confirmation", "reservation")):
        return "appointment_confirmation"
    if "newsletter" in s or "unsubscribe" in s:
        return "Admin/Newsletters"
    if domain.endswith(".gov.au"):
        return "Admin/Gov"
    return None


def index_summary(rules: list[Rule]) -> dict[str, Any]:
    """High-level counts for introspection / heartbeat logging."""
    by_consumer: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for r in rules:
        for c in r.consumers or ["none"]:
            by_consumer[c] = by_consumer.get(c, 0) + 1
        for k in r.action.keys():
            if r.action.get(k):
                by_action[k] = by_action.get(k, 0) + 1
    return {
        "total_rules": len(rules),
        "by_consumer": dict(sorted(by_consumer.items(), key=lambda x: -x[1])),
        "by_action": dict(sorted(by_action.items(), key=lambda x: -x[1])),
        "transient": sum(1 for r in rules if r.transient),
    }


def _rule_to_public_dict(r: Rule) -> dict[str, Any]:
    """Convert a Rule to a JSON-serialisable dict for CLI output."""
    d = dataclasses.asdict(r)
    d.pop("source_index", None)
    return {k: v for k, v in d.items() if v not in (None, "", [], {}, False)}


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--rules-file", type=Path, default=RULES_FILE, help="Path to email-rules.md"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "validate", help="Parse and validate the rules file; exit non-zero on errors"
    )
    sub.add_parser("stats", help="Print rule counts by consumer / action")
    sub.add_parser("index", help="Print all rules as JSON")

    m = sub.add_parser("match", help="Match a single synthetic message")
    m.add_argument("--from", dest="from_", required=True, help="From header value")
    m.add_argument("--subject", default="", help="Subject line")
    m.add_argument("--id", default=None, help="Optional message id for echo")

    mb = sub.add_parser(
        "match-batch", help="Match a batch of messages from a JSON file"
    )
    mb.add_argument("input", type=Path, help="Path to JSON list of {from, subject, id}")

    dr = sub.add_parser("draft-rule", help="Draft a rule block for an unknown sender")
    dr.add_argument("--from", dest="from_", required=True)
    dr.add_argument("--subject", default="")
    dr.add_argument("--label", default=None, help="Suggested label (optional)")

    args = parser.parse_args()
    rules = parse_rules_file(args.rules_file)

    if args.cmd == "validate":
        errs = validate_rules(rules)
        if errs:
            print(f"Found {len(errs)} validation error(s):", file=sys.stderr)
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 1
        print(f"OK — {len(rules)} rules validated cleanly.")
        return 0

    if args.cmd == "stats":
        print(json.dumps(index_summary(rules), indent=2))
        return 0

    if args.cmd == "index":
        print(json.dumps([_rule_to_public_dict(r) for r in rules], indent=2))
        return 0

    if args.cmd == "match":
        msg = {"from": args.from_, "subject": args.subject, "id": args.id}
        rule = match(msg, rules)
        if rule:
            print(
                json.dumps(
                    {"matched": True, "rule": _rule_to_public_dict(rule)}, indent=2
                )
            )
        else:
            print(json.dumps({"matched": False, "rule": None}, indent=2))
        return 0

    if args.cmd == "match-batch":
        messages = json.loads(args.input.read_text(encoding="utf-8"))
        print(json.dumps(match_batch(messages, rules), indent=2))
        return 0

    if args.cmd == "draft-rule":
        msg = {"from": args.from_, "subject": args.subject}
        print(draft_unknown_rule(msg, suggested_label=args.label))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(_cli())
