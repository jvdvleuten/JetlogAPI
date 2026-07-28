#!/usr/bin/env python3
"""Validate every example payload published in this repo.

Catches the class of mistake that is invisible to review but breaks integrators:
a payload that is not valid JSON, a deeplink whose encoded `data=` does not
decode, an example that violates a rule the docs themselves state, a curl
`-d` body that has drifted from the JSON block it illustrates, an orphan
"Open this example in Jetlog" link with nothing to pair it to, or a clickable
link whose encoded payload has drifted from the JSON block sitting right next
to it.

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
checked = {
    "json": 0,
    "curl": 0,
    "deeplink": 0,
    "links_matched": 0,
    "curl_matched": 0,
}


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


def is_deeplink_safe(payload: object) -> bool:
    """Mirrors the deeplink identity rule: non-empty entries, each with
    flight_number or registration."""
    if not isinstance(payload, dict):
        return False
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return False
    return all(
        isinstance(e, dict) and (e.get("flight_number") or e.get("registration")) for e in entries
    )


def decode_link(encoded: str) -> object:
    return json.loads(urllib.parse.unquote(encoded))


for name in DOCS:
    text = (ROOT / name).read_text()

    # --- Fenced json blocks that look like import request payloads, kept in
    # document order with their byte offsets so we can pair each one with the
    # nearest curl body and the nearest "Open this example in Jetlog" link
    # that follow it. Entries are (start_offset, end_offset,
    # parsed_payload_or_None). A response example (one with a top-level
    # "data" key) is never mixed in here — it never contains the substring
    # `"entries"` that gates this loop, since `skipped`/`warnings` rows carry
    # `date`/`flight_number`, not an `entries` key. ---
    json_blocks = []
    for m in re.finditer(r"```json\n(.*?)\n```", text, re.S):
        block = m.group(1)
        if '"entries"' not in block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as e:
            fail(f"{name} json block", f"invalid JSON: {e}")
            json_blocks.append((m.start(), m.end(), None))
            continue
        checked["json"] += 1
        json_blocks.append((m.start(), m.end(), payload))
        check_entries_payload(f"{name} json block", payload, deeplink=False)

    # --- curl `-d` request bodies, position-tracked so each one can be paired
    # with the JSON block it illustrates (same pairing style as the links
    # below): the copy an integrator actually pastes gets the same drift
    # check as the pretty-printed block next to it. ---
    curl_positions = []  # (start_offset, parsed_payload)
    for sh_m in re.finditer(r"```sh\n(.*?)\n```", text, re.S):
        block = sh_m.group(1)
        block_start = sh_m.start(1)
        for body_m in re.finditer(r"-d '(.*?)'", block, re.S):
            try:
                payload = json.loads(body_m.group(1))
            except json.JSONDecodeError as e:
                fail(f"{name} curl body", f"invalid JSON: {e}")
                continue
            checked["curl"] += 1
            check_entries_payload(f"{name} curl body", payload, deeplink=False)
            curl_positions.append((block_start + body_m.start(), payload))

    # --- Encoded deeplinks: the raw `jetlog://import?data=...` scheme form,
    # and the clickable `https://jetlog.app/import?data=...` launcher form
    # markdown links render as (the one that actually appears in the docs
    # now). Both carry the same `data=` contract. ---
    link_positions = []  # (start_offset, encoded_string, parsed_payload)

    for m in re.finditer(r"jetlog://import\?data=([^\s`\"\)]+)", text):
        encoded = m.group(1)
        if not encoded.startswith("%7B"):
            continue  # a placeholder like <encoded>, not a real link
        try:
            payload = decode_link(encoded)
        except json.JSONDecodeError as e:
            fail(f"{name} deeplink", f"`data=` does not decode to JSON: {e}")
            continue
        checked["deeplink"] += 1
        link_positions.append((m.start(), encoded, payload))
        check_entries_payload(f"{name} deeplink", payload, deeplink=True)

    for m in re.finditer(r"https://jetlog\.app/import\?data=([^\s`\")]+)", text):
        encoded = m.group(1)
        if not encoded.startswith("%7B"):
            continue  # a placeholder, not a real link
        try:
            payload = decode_link(encoded)
        except json.JSONDecodeError as e:
            fail(f"{name} jetlog.app link", f"`data=` does not decode to JSON: {e}")
            continue
        checked["deeplink"] += 1
        link_positions.append((m.start(), encoded, payload))
        check_entries_payload(f"{name} jetlog.app link", payload, deeplink=True)

    link_positions.sort(key=lambda t: t[0])

    # --- Every request JSON block (json_blocks only ever holds requests — a
    # response example has no top-level "entries" key, so it never passed the
    # gate above) is paired against whatever curl body and/or link sits in its
    # gap — from the end of this block up to the start of the next one. A curl
    # body is only compared when one is present in the gap (not every block
    # has a companion curl call, e.g. the bare payload-schema illustration).
    # A link, by contrast, is REQUIRED whenever the payload is deeplink-safe,
    # and exactly one is allowed: a second/orphan link in the same gap is an
    # error, not something to silently ignore. ---
    request_blocks = [(start, end, payload) for start, end, payload in json_blocks if payload is not None]
    for idx, (start, end, payload) in enumerate(request_blocks):
        where = f"{name} json block at offset {start}"

        next_block_start = (
            request_blocks[idx + 1][0] if idx + 1 < len(request_blocks) else len(text)
        )

        curl_candidate = next(
            (cp for cp in curl_positions if end <= cp[0] < next_block_start),
            None,
        )
        if curl_candidate is not None:
            _, curl_payload = curl_candidate
            if curl_payload != payload:
                fail(
                    where,
                    "the curl `-d` body's JSON does not match the adjacent JSON block",
                )
            else:
                checked["curl_matched"] += 1

        if not is_deeplink_safe(payload):
            continue  # this example was never meant to be opened as a link

        link_candidates = [lp for lp in link_positions if end <= lp[0] < next_block_start]
        if not link_candidates:
            fail(where, "deeplink-safe example has no matching Open-in-Jetlog link")
            continue
        if len(link_candidates) > 1:
            fail(
                where,
                f"{len(link_candidates)} Open-in-Jetlog links follow this example — "
                "expected exactly one (orphan link?)",
            )
            continue

        _, encoded, link_payload = link_candidates[0]
        if link_payload != payload:
            fail(
                where,
                "the Open-in-Jetlog link's decoded payload does not match the adjacent JSON block",
            )
        else:
            checked["links_matched"] += 1

# --- Global invariants: every curl body and every link found anywhere should
# have been claimed by exactly one pairing above. A leftover count here means
# something drifted past the per-example checks (e.g. two links in a gap,
# each individually "valid" JSON, silently averaging out). ---
if checked["curl_matched"] != checked["curl"]:
    fail(
        "global",
        f"{checked['curl']} curl bodies found but only {checked['curl_matched']} "
        "paired to a JSON block (orphan curl body?)",
    )
if checked["links_matched"] != checked["deeplink"]:
    fail(
        "global",
        f"{checked['deeplink']} deeplink/link occurrences found but only "
        f"{checked['links_matched']} paired 1:1 with a JSON block (orphan or "
        "unmatched link?)",
    )

total = checked["json"] + checked["curl"] + checked["deeplink"]
if errors:
    print(f"✗ {len(errors)} problem(s) in {total} example(s):\n")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(
    f"✓ {total} examples valid "
    f"({checked['json']} json, {checked['curl']} curl, {checked['deeplink']} deeplink/link, "
    f"{checked['links_matched']} links matched to their JSON block, "
    f"{checked['curl_matched']} curl bodies matched to their JSON block)"
)
