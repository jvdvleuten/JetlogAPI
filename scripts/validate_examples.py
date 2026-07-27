#!/usr/bin/env python3
"""Validate every example payload published in this repo.

Catches the class of mistake that is invisible to review but breaks integrators:
a payload that is not valid JSON, a deeplink whose encoded `data=` does not
decode, or an example that violates a rule the docs themselves state.

This is a docs-only check — it needs nothing but Python. It cannot tell you what
the server DOES with a payload; the two code repos own that:

  jetlog     test/jetlog_web/controllers/api/documented_examples_test.exs
  jetlog_ios JetlogCoreTests/Helpers/Importers/DocumentedDeeplinkExamplesTests.swift

Both mirror these payloads verbatim and assert the documented outcome. If you
change an example here, change it there too.

Usage: python3 scripts/validate_examples.py
"""

import json
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ["README.md", "EXAMPLES.md"]

errors: list[str] = []
checked = {"json": 0, "curl": 0, "deeplink": 0}


def fail(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def check_entries_payload(where: str, payload: object, *, deeplink: bool) -> None:
    """The rules the docs state for a payload, per flow."""
    if not isinstance(payload, dict):
        fail(where, "payload is not a JSON object")
        return

    entries = payload.get("entries")
    if not isinstance(entries, list):
        fail(where, "missing or non-list `entries`")
        return

    # Both flows now default an omitted top-level `people` key to `[]` and a
    # missing/null entry `type` to `"flight"` — no longer flagged as mistakes.

    for i, entry in enumerate(entries):
        at = f"{where} entries[{i}]"
        if not isinstance(entry, dict):
            fail(at, "entry is not an object")
            continue

        if deeplink and not (entry.get("flight_number") or entry.get("registration")):
            fail(at, "a deeplink entry needs `flight_number` or `registration`")

        if not deeplink and not (entry.get("from") and entry.get("to")):
            fail(at, "an API entry needs `from` and `to`")

        date = entry.get("date")
        if isinstance(date, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            fail(at, f"date {date!r} is not the documented YYYY-MM-DD")

        tal = entry.get("takeoffs_and_landings")
        if isinstance(tal, dict):
            auto = "takeoffs" in tal or "landings" in tal
            day_night = any(k in tal for k in ("takeoffs_day", "takeoffs_night", "landings_day", "landings_night"))
            if auto and not ("takeoffs" in tal and "landings" in tal):
                fail(at, "the `{takeoffs, landings}` shape must carry BOTH counts")
            if day_night and not all(
                k in tal for k in ("takeoffs_day", "takeoffs_night", "landings_day", "landings_night")
            ):
                fail(at, "the day/night shape must carry all four counts")
            # Both flows accept either shape now (day/night used to be API-only).


for name in DOCS:
    text = (ROOT / name).read_text()

    # Fenced json blocks that look like import payloads.
    for block in re.findall(r"```json\n(.*?)\n```", text, re.S):
        if '"entries"' not in block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as e:
            fail(f"{name} json block", f"invalid JSON: {e}")
            continue
        checked["json"] += 1
        # A response example, not a request.
        if "data" in payload:
            continue
        check_entries_payload(f"{name} json block", payload, deeplink=False)

    # curl request bodies.
    for block in re.findall(r"```sh\n(.*?)\n```", text, re.S):
        for body in re.findall(r"-d '(.*?)'", block, re.S):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as e:
                fail(f"{name} curl body", f"invalid JSON: {e}")
                continue
            checked["curl"] += 1
            check_entries_payload(f"{name} curl body", payload, deeplink=False)

    # Encoded deeplinks.
    for encoded in re.findall(r"jetlog://import\?data=([^\s`\"]+)", text):
        if not encoded.startswith("%7B"):
            continue  # a placeholder like <encoded>, not a real link
        try:
            payload = json.loads(urllib.parse.unquote(encoded))
        except json.JSONDecodeError as e:
            fail(f"{name} deeplink", f"`data=` does not decode to JSON: {e}")
            continue
        checked["deeplink"] += 1
        check_entries_payload(f"{name} deeplink", payload, deeplink=True)

total = sum(checked.values())
if errors:
    print(f"✗ {len(errors)} problem(s) in {total} example(s):\n")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(
    f"✓ {total} examples valid "
    f"({checked['json']} json, {checked['curl']} curl, {checked['deeplink']} deeplink)"
)
