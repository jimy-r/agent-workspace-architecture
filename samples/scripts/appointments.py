"""Appointment extraction helper — validates agent-extracted appointment payloads and
formats them for the `google-calendar` MCP `create-event` tool.

The agent reads Gmail messages classified as `appointment_confirmation` (via the
email-rules registry), extracts the appointment details with its own reasoning, then
calls this script to validate + format. The agent then calls the Calendar MCP with
the formatted payload, and appends the source-id token into the event description so
future runs can dedupe.

Dedup strategy: the event's description includes `[source: gmail:<messageId>]`. The
agent queries Calendar before creating an event; if `search-events` returns a match
for the source token, skip.

Appointment schema (input JSON):
{
  "title": "GP — Dr Smith",                   # required
  "start": "2026-04-25T10:30:00+10:00",       # required, ISO8601 with tz
  "end":   "2026-04-25T11:00:00+10:00",       # required
  "location": "Level 3, 123 Queen St <city>", # optional
  "confirmation_id": "APPT-88213",            # optional, goes in description
  "source_msg_id": "1234567890abcdef",         # required, Gmail messageId for dedup
  "notes": "Bring referral letter"             # optional
}

Usage:
  python appointments.py validate appointments.json
  python appointments.py format --json '{...}'
  python appointments.py dedup-token --source-msg-id <id>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {"title", "start", "end", "source_msg_id"}
DEFAULT_CALENDAR = "primary"


def validate_appointment(raw: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    # Error text names fields only, never values: the callers print it to stderr.
    missing = sorted(f for f in REQUIRED_FIELDS if f not in raw)
    if missing:
        errs.append(f"missing required fields: {missing}")
    for fld in ("start", "end"):
        if fld in raw:
            val = str(raw[fld])
            try:
                datetime.fromisoformat(val)
            except ValueError:
                errs.append(f"{fld} not ISO8601")
    if "start" in raw and "end" in raw:
        try:
            s = datetime.fromisoformat(str(raw["start"]))
            e = datetime.fromisoformat(str(raw["end"]))
            if e <= s:
                errs.append("end must be after start")
        except ValueError:
            pass
    if "title" in raw and not str(raw["title"]).strip():
        errs.append("title is empty")
    if "source_msg_id" in raw and not str(raw["source_msg_id"]).strip():
        errs.append("source_msg_id is empty")
    return errs


def dedup_token(source_msg_id: str) -> str:
    """The string embedded in event descriptions so future runs can dedupe."""
    return f"[source: gmail:{source_msg_id}]"


def format_event_payload(
    appt: dict[str, Any], calendar_id: str = DEFAULT_CALENDAR
) -> dict[str, Any]:
    """Return a dict ready to pass to `mcp__google-calendar__create-event`.

    Structure matches the MCP tool's expected schema:
    - calendarId, summary, location, description, start {dateTime,timeZone}, end {...}
    """
    description_lines: list[str] = []
    if appt.get("notes"):
        description_lines.append(str(appt["notes"]))
    if appt.get("confirmation_id"):
        description_lines.append(f"Confirmation: {appt['confirmation_id']}")
    description_lines.append("")
    description_lines.append(dedup_token(str(appt["source_msg_id"])))

    start_iso = str(appt["start"])
    end_iso = str(appt["end"])

    payload: dict[str, Any] = {
        "calendarId": calendar_id,
        "summary": str(appt["title"]).strip(),
        "description": "\n".join(description_lines).strip(),
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if appt.get("location"):
        payload["location"] = str(appt["location"]).strip()
    return payload


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    val = sub.add_parser("validate", help="Validate a JSON file of appointments")
    val.add_argument("input", type=Path)

    fmt = sub.add_parser("format", help="Format a single appointment for Calendar MCP")
    fmt.add_argument("--json", dest="json_str", required=True)
    fmt.add_argument("--calendar-id", default=DEFAULT_CALENDAR)

    dt = sub.add_parser(
        "dedup-token", help="Print the source-token used in event descriptions"
    )
    dt.add_argument("--source-msg-id", required=True)

    args = parser.parse_args()

    if args.cmd == "validate":
        items = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            items = [items]
        total_errs = 0
        for i, raw in enumerate(items):
            errs = validate_appointment(raw)
            if errs:
                total_errs += 1
                print(f"[{i}] invalid: {errs}", file=sys.stderr)
        if total_errs:
            return 1
        print(f"OK — {len(items)} appointment(s) validate cleanly.")
        return 0

    if args.cmd == "format":
        appt = json.loads(args.json_str)
        errs = validate_appointment(appt)
        if errs:
            print(json.dumps({"errors": errs}, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(format_event_payload(appt, args.calendar_id), indent=2))
        return 0

    if args.cmd == "dedup-token":
        print(dedup_token(args.source_msg_id))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(_cli())
