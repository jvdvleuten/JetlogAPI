# Jetlog Import Guide

Two ways to bring flights into Jetlog:
- **Deeplink (jetlog://import?data=…)** – for end users/scripts that can open the Jetlog app.
- **External Partner API (https://jetlog.app/external/v1/import)** – HTTP endpoint with dual-key auth (`Bearer <user_key>:<partner_key>`).

The **JSON payload is the same** for both flows (see “Payload schema” below).

Ready-to-use payloads, encoded deeplinks and curl calls: **[EXAMPLES.md](EXAMPLES.md)**.

Every example in this repo is validated by `python3 scripts/validate_examples.py`, and both flows' payloads are asserted against the real importers by tests in the backend and iOS repos — so an example that stops working fails a build rather than misleading you.

## Payload schema (shared)
Top-level keys:
```json
{
  "entries": [],
  "people": []
}
```

**Flight Entry (`entries`):**
| Field                  | Type   | Required | Description                               |
| :--------------------- | :----- | :------- | :---------------------------------------- |
| `type`                 | String | No       | Defaults to `"flight"` — a missing key or an explicit `null` both count as the default. Only `"flight"` is supported; any other value is not imported (see each flow's Behavior section for how that's reported). |
| `date`                 | String | Yes      | `YYYY-MM-DD`.                             |
| `flight_number`        | String | No       | Flight number.                            |
| `scheduled_off_blocks` | String | No       | Planned off-blocks, `HH:MM` zulu.         |
| `scheduled_on_blocks`  | String | No       | Planned on-blocks, `HH:MM` zulu.          |
| `registration`         | String | No       | Aircraft registration. Normalised to uppercase with separators stripped (`PH-BXD` → `PHBXD`). |
| `from`                 | String | No       | ICAO departure. A 3-letter IATA code is converted when recognised; an unrecognised one is stored as given. |
| `to`                   | String | No       | ICAO arrival. Same IATA handling as `from`. |
| `off_blocks`           | String | No       | `HH:MM` zulu.                             |
| `airborne`             | String | No       | `HH:MM` zulu.                             |
| `touchdown`            | String | No       | `HH:MM` zulu.                             |
| `on_blocks`            | String | No       | `HH:MM` zulu.                             |
| `people`               | Array  | No       | Crew list (see below).                    |
| `takeoffs_and_landings`| Object | No       | `{ "takeoffs": n, "landings": n }`, or the day/night split `{ "takeoffs_day": n, "takeoffs_night": n, "landings_day": n, "landings_night": n }` — send **both** counts of whichever shape you use. Both flows accept either shape. |
| `remarks`              | String | No       | Free text, max 1000 characters. **Never overwrites remarks the entry already has** — see the per-flow rules below. |
| `is_deleted`           | Bool   | No       | Soft-delete an entry this caller created. `false` restores one. |
| `update_flight_data`   | Bool   | No       | Auto-update from external sources. An explicit value always applies. When omitted, both flows infer it: on **create**, `false` if any actual time (`off_blocks`/`airborne`/`touchdown`/`on_blocks`) is supplied — so your reported times are what's shown — else `true`; on a **re-import/merge** of an existing entry, the inferred switch to `false` happens only when the import actually brings a new or changed actual time, otherwise the entry's stored setting is left untouched (a byte-identical re-import never flips it). |

**Flight `people` object:**
| Field    | Type   | Required | Description                                                          |
| :------- | :----- | :------- | :------------------------------------------------------------------- |
| `ref_id` | String | Yes      | References `people.ref_id`, or `"SELF"` for yourself.               |
| `role`   | String | Yes      | Role on this flight (e.g. PIC, CP, Purser).                         |

**Person Entry (`people`):**
| Field             | Type   | Required | Description                        |
| :---------------- | :----- | :------- | :--------------------------------- |
| `ref_id`          | String | Yes      | Unique ID; reused in entries.      |
| `first_name`      | String | Yes      | First name.                        |
| `last_name`       | String | Yes      | Last name.                         |
| `default_role`    | String | No       | Default role.                      |
| `employee_number` | String | No       | Employee number.                   |

**Notes on people**
- You can use `SELF` in a flight without adding a top-level person for yourself.
- `ref_id` is payload-local: it links `entries[*].people[*].ref_id` to `people[*].ref_id` and is not stored.
- Whether an existing person can be modified by the payload differs per flow — for the External Partner API, see "People" under its Behavior section below.

**A JSON `null` means "key omitted"**

Both flows treat an explicit `null` on any entry or person field exactly like
leaving the key out — there's no separate "clear this field" meaning. For
example: `"type": null` defaults to `"flight"` just like a missing `type`;
`"is_deleted": null` is treated as if `is_deleted` weren't mentioned at all
(so a same-source soft-deleted match is reported as `"deleted"`, not
resurrected — see the skip reasons below); `"remarks": null`,
`"update_flight_data": null`, and the time fields all fall back to their
normal omitted-key behavior the same way.

This extends to the top level: `"entries": null` or `"people": null` are
treated as `[]`. Anything else that isn't a list there (a string, a number,
an object) — or a list containing anything that isn't an object, like
`"entries": [null]` — is rejected outright with a 400
`{"error": "invalid_payload"}` — a stable string, never a 500. One level
down, an entry whose own `people` value isn't a list of objects skips just
that row as `"invalid_field"` (with `"people"` in `fields`); sibling rows
still import.

**Remarks are never silently overwritten**

Remarks are the pilot's own text, so an import can add them but not quietly replace them:

- **External Partner API** — write-once. Remarks are written whenever the entry has none, so you can add them on a later import of a flight you sent earlier without them. Once an entry *has* remarks they are never replaced — whoever wrote them, your own earlier import or the pilot in the app. A partner cannot correct its own earlier remark.
- **Deeplink** — the import preview shows the remarks change as `existing → new` before anything is written, and offers a **Replace / Add** choice on that row. `Add` keeps the stored note and appends the imported text after it; re-importing the same text twice does not stack it. When the entry has no remarks yet, the imported value is simply written and no choice is offered.

**Where the two flows differ**

`people`, `type`, the *shape* of `takeoffs_and_landings` (plain vs. day/night), non-`"flight"` rows, and the `update_flight_data` inference (see the field table above) are all handled the same way now (optional/defaulted/tolerated on both). What's left genuinely differs — check these if you support both:

| | Deeplink | External Partner API |
| :-- | :-- | :-- |
| Entry required fields | `flight_number` **or** `registration` | `from` **and** `to` |
| An incomplete `{takeoffs, landings}` pair (only one of the two counts sent) — or an unrecognised explicit `takeoffs_and_landings.type` (anything other than `"auto"`/`"manual"`) | Entry still imports; only the counts are dropped, flagged as a per-row error in the import preview | Whole row skipped — `"invalid_field"`, e.g. `"fields": ["takeoffs_and_landings.landings"]` |
| `remarks` on a re-import | Replace / Add choice in the preview | Write-once; never overwritten |
| Unresolvable `people[].ref_id` | Kept for the import review to resolve | Entry still imports without that crew member; reported in the response's `warnings` array |
| Matching an existing person | May update their `default_role`, but only when the payload actually supplies one — omitting it never wipes an existing role; also matches on a single name | Never modifies an existing person; matches `employee_number` then first+last only |

## Deeplink Import

**URL format**
```
jetlog://import?data=<URL_ENCODED_JSON_STRING>
```
Steps:
1) Build JSON per schema above.  
2) URL-encode the JSON string.  
3) Open `jetlog://import?data=<encoded>` (click or `open "jetlog://..."`).  

**JSON example**
```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2025-12-10",
      "flight_number": "KL1023",
      "scheduled_off_blocks": "14:00",
      "registration": "PH-BXD",
      "from": "EHAM",
      "to": "EGLL",
      "off_blocks": "14:08",
      "airborne": "14:28",
      "touchdown": "14:55",
      "on_blocks": "15:05",
      "people": [
        {"ref_id": "SELF", "role": "PIC"},
        {"ref_id": "REF2", "role": "FO"},
        {"ref_id": "REF3", "role": "Purser"}
      ],
      "takeoffs_and_landings": {"takeoffs": 1, "landings": 1}
    }
  ],
  "people": [
    {"ref_id": "REF2", "first_name": "Fantas", "last_name": "Tico", "default_role": "FO", "employee_number": "00923"},
    {"ref_id": "REF3", "first_name": "Sally", "last_name": "Skyway", "default_role": "Purser", "employee_number": "01556"}
  ]
}
```

**Important notes**
- URL length: split if payloads are huge.
- `type` may be omitted (or sent as `null`) — it defaults to `"flight"`. Any other value, or a structurally malformed entry/person (bad types, a missing required key), is not silently dropped: it shows up as a per-row error in the import review instead, and the rest of the payload still imports.
- The top-level `people` key may be omitted — treated the same as `[]`.
- Errors: invalid fields/refs may yield partial or failed imports; see the row-error behavior above.
- Times are `HH:MM` zulu relative to the flight date.
- Opening a link never writes anything on its own — the app shows an import preview the user confirms.
- A row that deletes an existing entry (`is_deleted: true`) is called out in that preview and **starts unselected**: the user has to opt in before it is applied. Don't rely on a link alone to remove a flight.

## External Partner API

**Authentication**
- Header: `Authorization: Bearer <user_key>:<partner_key>`
- `user_key`: server-generated when a user enables the external source.
- `partner_key`: issued per integration.

**Endpoint**
```
POST /external/v1/import
Content-Type: application/json
Authorization: Bearer <user_key>:<partner_key>
```

**Behavior**
- Entry match: per user by `date + flight_number + from + to`; updates or creates accordingly.
- Required fields: `from` and `to` must be provided for the External Partner API.
- Soft-delete: `is_deleted: true` deletes only the caller's own external entries. Sending `is_deleted: false` for the same flight restores one you previously deleted.
- Re-importing a flight you've soft-deleted: if the row doesn't mention `is_deleted` at all, it is skipped (reason `"deleted"`) rather than silently un-deleting a row this caller can no longer see. Send `is_deleted: false` to actually restore it.
- Entries from another source (the app itself, a roster import, another partner) are never modified — they come back as `"duplicate"` in `skipped`. This is about *live* rows only: if that other source's entry is itself soft-deleted, its identity is free — importing the same flight creates a new, live row alongside the deleted one rather than resurrecting or merging into it.
- People:
  - A submitted person is matched against the people the user already has: first by `employee_number`, otherwise by `first_name` + `last_name` (ignoring case and surrounding whitespace).
  - **A matched person is reused but never modified.** The API will not rename an existing contact, change their `default_role`, or alter their `employee_number` — this includes the user's own profile. Only a person matching nothing is created, using every field supplied.
  - `SELF` = the authenticated user. A submitted person that matches the user's own profile resolves to it instead of creating a duplicate contact.
  - Two `ref_id`s resolving to the same person collapse to one crew assignment on an entry (the first `role` wins). A `ref_id` that resolves to nothing does not fail the entry: it imports without that crew member, and the response's `warnings` array gets an entry for it (see below).
  - Crew is merged, never replaced: omitting `people` — or sending `[]` — on a re-import keeps the existing crew. There is no way to remove crew from an entry via this API.
- Success: `{"data": "OK", "skipped": [...]}`, plus an additive `"warnings"` array when there's something to report (omitted entirely otherwise). Errors return `{"error": "<message>"}` where `<message>` is always one of a short, stable set of strings (e.g. `"invalid_user"`, `"update_failed"`, `"import_failed"`) — never a raw changeset, stack trace, or internal id.
- Skipped reasons:
  - `"duplicate"`: entry matches an existing entry from a different source (fields: `date`, `flight_number`, `from`, `to`, `reason`).
  - `"missing_route"`: entry lacks `from` and `to` (fields: `date`, `flight_number`, `reason`).
  - `"unsupported_type"`: entry `type` is not `"flight"` (fields: `date`, `flight_number`, `type`, `reason`). Nothing is stored for it.
  - `"duplicate_in_payload"`: this same `(date, flight_number, from, to)` identity appears more than once in this payload; the **last** occurrence is imported and the earlier one(s) are reported this way (fields: `date`, `flight_number`, `from`, `to`, `reason`).
  - `"deleted"`: a same-source entry with this identity exists but is soft-deleted, and this row doesn't say anything about `is_deleted` (fields: `date`, `flight_number`, `from`, `to`, `reason`). Send `is_deleted: false` to restore it instead.
  - `"invalid_field"`: the row failed the same field-level validation a direct write would (an unparsable time, an incomplete `takeoffs_and_landings` pair, ...) — only this row is skipped (fields: `date`, `flight_number`, `reason`, `fields` — an array of the failing field names). A field inside an embedded object like `takeoffs_and_landings` is named with a dot, e.g. `"takeoffs_and_landings.landings"` for a missing landings count — not just `"landings"`.
- Warnings: an entry that imports but references a `people[].ref_id` that doesn't resolve to a known person adds one entry to the top-level `"warnings"` array: `{"date", "flight_number", "ref_id", "reason": "unresolved_person_ref"}`. The flight itself still imports, just without that crew member.
- Rows are independent: a skipped, deleted, or invalid row never prevents the rest of the payload from importing. A request that can't be processed at all (bad auth, unparsable JSON, a batch-level failure) returns a non-200 `{"error": "..."}`. This does **not** always mean nothing was written: `people` and `entries` are committed in separate transactions, people first — if the batch fails while processing `entries`, any `people` rows that were newly created from this same payload are already persisted even though the request as a whole reports non-200. It's safe to resend the same payload afterward: those people will simply match on the retry instead of being duplicated.

**Example request**
```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer USER_KEY:PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entries":[
      {
        "type":"flight",
        "date":"2025-12-10",
        "flight_number":"KL1023",
        "from":"EHAM",
        "to":"EGLL",
        "people":[{"ref_id":"SELF","role":"PIC"}]
      }
    ],
    "people":[]
  }'
```

**Example response**
```json
{"data": "OK", "skipped": []}
```

With skipped entries:
```json
{
  "data": "OK",
  "skipped": [
    {"date": "2025-12-10", "flight_number": "KL1023", "from": "EHAM", "to": "EGLL", "reason": "duplicate"},
    {"date": "2025-12-11", "flight_number": "KL2000", "reason": "missing_route"},
    {"date": "2025-12-12", "flight_number": "KL2101", "reason": "invalid_field", "fields": ["off_blocks"]},
    {"date": "2025-12-13", "flight_number": "KL2201", "reason": "invalid_field", "fields": ["takeoffs_and_landings.landings"]}
  ]
}
```

With a warning (the entry itself still imports, just without the crew member that didn't resolve):
```json
{
  "data": "OK",
  "skipped": [],
  "warnings": [
    {"date": "2025-12-13", "flight_number": "KL2200", "ref_id": "REF9", "reason": "unresolved_person_ref"}
  ]
}
```

## Tips
- Keep `ref_id` unique in `people`; reuse in `entries[*].people`.
- Use UTC for times; `date` is `YYYY-MM-DD`.
- Batch large external imports; split deeplinks if URLs get too long.
