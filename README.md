# Jetlog Import Guide

## Quick start

Two ways to bring flights into Jetlog:
- **Deeplink (jetlog://import?data=…)** – for end users/scripts that can open the Jetlog app.
- **External Partner API (https://jetlog.app/external/v1/import)** – HTTP endpoint with dual-key auth (`Bearer <user_key>:<partner_key>`).

The **JSON payload is the same** for both flows (see "Payload schema" below).

**Auth, in one line:** External Partner API calls send `Authorization: Bearer <user_key>:<partner_key>` — `user_key` is server-generated when a user enables the external source, `partner_key` is issued per integration. Full details are under [External Partner API](#external-partner-api) in the Reference part below.

**The minimal payload** — identity for the deeplink, route for the API, nothing else required:

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-14",
      "flight_number": "KL1023",
      "from": "EHAM",
      "to": "EGLL"
    }
  ],
  "people": []
}
```

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL"}],"people":[]}'
```

[▶ Open this example in Jetlog](https://jetlog.app/import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-14%22%2C%22flight_number%22%3A%22KL1023%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%7D%5D%2C%22people%22%3A%5B%5D%7D)

*Opening that link requires the Jetlog app; without it you land on an explanation page instead of a silent failure. Every other `jetlog.app/import` link in this repo and in EXAMPLES.md behaves the same way.*

Ready-to-use payloads for every field, crew, clearing a value, deleting a flight, day/night landings, and IATA conversion — each with its own clickable link and curl call: **[EXAMPLES.md](EXAMPLES.md)**.

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
| :--------------------- | :----- | :------- | :----------------------------------------- |
| `type`                 | String | No       | Defaults to `"flight"` — a missing key or an explicit `null` both count as the default. Only `"flight"` is supported; any other value is not imported (see each flow's Behavior section for how that's reported). |
| `date`                 | String | Yes      | `YYYY-MM-DD`.                             |
| `flight_number`        | String | No       | Flight number.                            |
| `scheduled_off_blocks` | String | No       | Planned off-blocks, `HH:MM` zulu. `null` is treated as omitted, same as leaving the key out — this is **not** one of the clearable fields, because the flight-data feed refills a nil scheduled column itself (backend enrichment does it in the same request) and the field has no per-field timestamp, so a "clear" can't stick. |
| `scheduled_on_blocks`  | String | No       | Planned on-blocks, `HH:MM` zulu. Same as `scheduled_off_blocks` — `null` is treated as omitted, not a clear. |
| `registration`         | String | No       | Aircraft registration. Normalised to uppercase with separators stripped (`PH-BXD` → `PHBXD`). **Clearable** — an explicit `null` clears the stored (manual) registration; it does not touch the separately-tracked system-sourced value (`registration_system`), so while `update_flight_data` is `true` the system-sourced tail can still display after the clear. A partner-created entry seeds `registration_system` at create. |
| `from`                 | String | No       | ICAO departure. A 3-letter IATA code is converted when recognised; an unrecognised one is stored as given. |
| `to`                   | String | No       | ICAO arrival. Same IATA handling as `from`. |
| `off_blocks`           | String | No       | `HH:MM` zulu. **Clearable** — an explicit `null` clears a stored value on a match; omitting the key leaves it untouched. |
| `airborne`             | String | No       | `HH:MM` zulu. **Clearable**, same as `off_blocks`. |
| `touchdown`            | String | No       | `HH:MM` zulu. **Clearable**, same as `off_blocks`. |
| `on_blocks`            | String | No       | `HH:MM` zulu. **Clearable**, same as `off_blocks`. |
| `people`               | Array  | No       | Crew list (see below). `null` is treated as omitted — crew is merge-only, never wiped. |
| `takeoffs_and_landings`| Object | No       | `{ "takeoffs": n, "landings": n }`, or the day/night split `{ "takeoffs_day": n, "takeoffs_night": n, "landings_day": n, "landings_night": n }` — send **both** counts of whichever shape you use. Both flows accept either shape. **Clearable** — an explicit `null` clears it: the entry reads as 0 takeoffs / 0 landings, untracked. |
| `remarks`              | String | No       | Free text, max 1000 characters. **Never overwrites remarks the entry already has**, and `null` is always treated as omitted (never a wipe) — see the per-flow rules below. |
| `is_deleted`           | Bool   | No       | Soft-delete an entry this caller created. `false` restores one. `null` is treated as omitted — deletion state only ever changes on an explicit `true`/`false`. |
| `update_flight_data`   | Bool   | No       | Auto-update the entry from Jetlog's flight data sources (live airline/airport feeds — unrelated to this API). An explicit value always applies; `null` is treated as omitted, falling through to inference. On **create**, inference is `false` if any actual time (`off_blocks`/`airborne`/`touchdown`/`on_blocks`) is supplied with a real, non-`null` value — so your reported times are what's shown — else `true`; a `null` on one of those fields is a clear, not a supplied time, and never triggers this. On a **re-import/merge** of an existing entry, the inferred switch to `false` happens only when the import actually brings a new or changed non-`null` actual time; a `null` (a clear) never counts as "differing", so a row that only clears a time leaves the stored setting untouched, and a byte-identical re-import never flips it either. |

**Flight `people` object:**
| Field    | Type   | Required | Description                                                          |
| :------- | :----- | :------- | :--------------------------------------------------------------------- |
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
- Whether an existing person can be modified by the payload differs per flow — for the External Partner API, see "People" under its Behavior section in Reference below.

## Reference

The deep semantics for both flows — read this when a payload doesn't behave the way you expected. Everything above is what you need for the common case.

### What a JSON `null` means depends on the field

Both flows follow the same two-tier rule for an explicit `null` on an entry
field:

**(a) Clearable value fields — `null` clears, omitting leaves untouched.**
`off_blocks`, `airborne`, `touchdown`, `on_blocks`, `registration`, and
`takeoffs_and_landings` — six fields — treat an explicit `null` on a
matching existing entry exactly like the normal sync upsert's clear: the
value is removed. Leaving the key out of the payload entirely, by contrast,
leaves whatever is already stored untouched — only a *literal* `null`
clears. Worked example: to blank out an `off_blocks` you imported earlier,
re-send the same identity with `"off_blocks": null`; the entry's other
fields (e.g. `airborne`) are untouched. On the External Partner API this
flows through the normal changeset like any other edit — each of these six
fields has its own per-field timestamp, which is bumped to "now", so the
clear syncs to other devices exactly like a real edit — and, since the amend
path only ever matches the caller's own previously-imported rows, a clear
can never land on an entry another source or the pilot's own app wrote.
`registration` is a partial exception in what it displays afterward: the
clear only ever touches the manual `registration` column, never the
separately-tracked `registration_system` (a partner-created entry seeds that
column at create), so while `update_flight_data` is `true` the system-sourced
tail can still be what's shown right after the clear.

**(b) These fields keep the old rule: `null` is always treated as "key
omitted", never a clear** — each for its own reason:
- `type` — `NOT NULL` with no meaningful clear; a missing key or an explicit
  `null` both just mean the default, `"flight"`.
- `is_deleted` — `NOT NULL`; deletion state only ever changes on an explicit
  `true`/`false`, so a same-source soft-deleted match with `null` (or no
  mention at all) still reports `"deleted"` rather than being resurrected —
  see the skip reasons below.
- `update_flight_data` — `NOT NULL` with a schema default; "cleared" doesn't
  mean anything against the inference, so `null` just falls through to it.
- `people` — crew is merge-only by contract; a `null` must never wipe the
  crew list.
- `remarks` — write-once/consent semantics own this field on both flows; a
  `null` must never be a remarks wipe (and clearing a blank note would be a
  no-op anyway).
- `scheduled_off_blocks` / `scheduled_on_blocks` — the flight-data feed
  refills a nil scheduled column itself (backend enrichment does this in the
  same request), and neither field carries a per-field timestamp, so a
  client-issued clear has nothing to hold the line against the feed and
  would not stick. These moved out of the clearable set for exactly that
  reason — a "clear" here can't be honored, so it isn't promised.

**(c) Identity fields can't be cleared — by construction, not by
special-casing.** On the External Partner API, `from`/`to` sent as `null`
simply fails the `"missing_route"` requirement, so nothing is written — there
is nothing to clear. A `null` `date` or `flight_number` just participates in
matching as `nil`, and under SQL `NULL` semantics that can never *find* a row
that already has a real value, so a "clear" via either is unreachable. On the
deeplink, identity is `flight_number` **or** `registration`: if `registration`
is nulled but `flight_number` still identifies the row, the clear still
applies to the matched entry (`registration` is one of the clearable value
fields above); if both are `nil`, it's the existing per-row missing-identity
error, same as before.

**(d) `""` is never a clear — don't send it.** Only a *literal* JSON `null`
clears (the (a) fields) or falls through to a default/inference (the (b)
fields); send the key as `null` or leave it out to be unambiguous. What `""`
actually does differs per flow:

- **External Partner API** — `""` is ignored for *every* field, treated as
  if the key were left out entirely: it never clears a stored value and
  never writes one. `"is_deleted": ""` does not resurrect a soft-deleted
  entry, and `"update_flight_data": ""` does not flip it to `true`.
- **Deeplink** — `""` in a text/time field (`registration`, the times) is
  unparsable and ignored; but `"type": ""` fails that row as an unsupported
  type, and `""` in a boolean field (`is_deleted`, `update_flight_data`)
  fails the row as malformed — both show up as per-row errors in the import
  review.

The deeplink shows every clear in its import preview — a "→ (empty)" line,
same as any other field change — before anything is written, so the user
always sees and confirms it.

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

`people`, `type`, the *shape* of `takeoffs_and_landings` (plain vs. day/night), non-`"flight"` rows, the `update_flight_data` inference, and the null-clears-a-value-field rule (see the field table and ["What a JSON `null` means"](#what-a-json-null-means-depends-on-the-field) above) are all handled the same way now (optional/defaulted/tolerated/clearable on both). What's left genuinely differs — check these if you support both:

| | Deeplink | External Partner API |
| :-- | :-- | :-- |
| Entry required fields | `flight_number` **or** `registration` | `from` **and** `to` |
| An incomplete `{takeoffs, landings}` pair (only one of the two counts sent) — or an unrecognised explicit `takeoffs_and_landings.type` (anything other than `"auto"`/`"manual"`) | Entry still imports; only the counts are dropped, flagged as a per-row error in the import preview | Whole row skipped — `"invalid_field"`, e.g. `"fields": ["takeoffs_and_landings.landings"]` |
| `remarks` on a re-import | Replace / Add choice in the preview | Write-once; never overwritten |
| Unresolvable `people[].ref_id` | Kept for the import review to resolve | Entry still imports without that crew member; reported in the response's `warnings` array |
| Matching an existing person | May update their `default_role`, but only when the payload actually supplies one — omitting it never wipes an existing role; also matches on a single name | Never modifies an existing person; matches `employee_number` then first+last only |

### Deeplink Import

**URL format**
```
jetlog://import?data=<URL_ENCODED_JSON_STRING>
```
Steps:
1) Build JSON per schema above.  
2) URL-encode the JSON string.  
3) Open `jetlog://import?data=<encoded>` (click or `open "jetlog://..."`).  

The same `?data=` contract also works behind `https://jetlog.app/import?data=<encoded>` — that's the form you put in a web page or README, since a custom scheme isn't clickable there; the app parses both identically. See "Building a deeplink yourself" in EXAMPLES.md.

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

[▶ Open this example in Jetlog](https://jetlog.app/import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222025-12-10%22%2C%22flight_number%22%3A%22KL1023%22%2C%22scheduled_off_blocks%22%3A%2214%3A00%22%2C%22registration%22%3A%22PH-BXD%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22off_blocks%22%3A%2214%3A08%22%2C%22airborne%22%3A%2214%3A28%22%2C%22touchdown%22%3A%2214%3A55%22%2C%22on_blocks%22%3A%2215%3A05%22%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%2C%7B%22ref_id%22%3A%22REF2%22%2C%22role%22%3A%22FO%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22role%22%3A%22Purser%22%7D%5D%2C%22takeoffs_and_landings%22%3A%7B%22takeoffs%22%3A1%2C%22landings%22%3A1%7D%7D%5D%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22REF2%22%2C%22first_name%22%3A%22Fantas%22%2C%22last_name%22%3A%22Tico%22%2C%22default_role%22%3A%22FO%22%2C%22employee_number%22%3A%2200923%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22first_name%22%3A%22Sally%22%2C%22last_name%22%3A%22Skyway%22%2C%22default_role%22%3A%22Purser%22%2C%22employee_number%22%3A%2201556%22%7D%5D%7D)

This same payload also imports unmodified through the External Partner API — the schema really is shared, not just similar.

**Important notes**
- URL length: split if payloads are huge.
- `type` may be omitted (or sent as `null`) — it defaults to `"flight"`. Any other value, or a structurally malformed entry/person (bad types, a missing required key), is not silently dropped: it shows up as a per-row error in the import review instead, and the rest of the payload still imports.
- The top-level `people` key may be omitted — treated the same as `[]`.
- Errors: invalid fields/refs may yield partial or failed imports; see the row-error behavior above.
- Times are `HH:MM` zulu relative to the flight date.
- Opening a link never writes anything on its own — the app shows an import preview the user confirms.
- A row that deletes an existing entry (`is_deleted: true`) is called out in that preview and **starts unselected**: the user has to opt in before it is applied. Don't rely on a link alone to remove a flight.

### External Partner API

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

#### Skip reasons and warnings — the full list

- `"duplicate"`: entry matches an existing entry from a different source (fields: `date`, `flight_number`, `from`, `to`, `reason`).
- `"missing_route"`: entry lacks `from` and `to` (fields: `date`, `flight_number`, `reason`).
- `"unsupported_type"`: entry `type` is not `"flight"` (fields: `date`, `flight_number`, `type`, `reason`). Nothing is stored for it.
- `"duplicate_in_payload"`: this same `(date, flight_number, from, to)` identity appears more than once in this payload; the **last** occurrence is imported and the earlier one(s) are reported this way (fields: `date`, `flight_number`, `from`, `to`, `reason`).
- `"deleted"`: a same-source entry with this identity exists but is soft-deleted, and this row doesn't say anything about `is_deleted` (fields: `date`, `flight_number`, `from`, `to`, `reason`). Send `is_deleted: false` to restore it instead.
- `"invalid_field"`: the row failed the same field-level validation a direct write would (an unparsable time, an incomplete `takeoffs_and_landings` pair, ...) — only this row is skipped (fields: `date`, `flight_number`, `reason`, `fields` — an array of the failing field names). A field inside an embedded object like `takeoffs_and_landings` is named with a dot, e.g. `"takeoffs_and_landings.landings"` for a missing landings count — not just `"landings"`.

Warnings: an entry that imports but references a `people[].ref_id` that doesn't resolve to a known person adds one entry to the top-level `"warnings"` array: `{"date", "flight_number", "ref_id", "reason": "unresolved_person_ref"}`. The flight itself still imports, just without that crew member.

Rows are independent: a skipped, deleted, or invalid row never prevents the rest of the payload from importing. A request that can't be processed at all (bad auth, unparsable JSON, a batch-level failure) returns a non-200 `{"error": "..."}`. This does **not** always mean nothing was written: `people` and `entries` are committed in separate transactions, people first — if the batch fails while processing `entries`, any `people` rows that were newly created from this same payload are already persisted even though the request as a whole reports non-200. It's safe to resend the same payload afterward: those people will simply match on the retry instead of being duplicated.

**Example request**

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2025-12-10",
      "flight_number": "KL1023",
      "from": "EHAM",
      "to": "EGLL",
      "people": [{"ref_id": "SELF", "role": "PIC"}]
    }
  ],
  "people": []
}
```

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

This payload is also deeplink-valid — clicking it opens the same import in the app, confirming the schema is shared in both directions:

[▶ Open this example in Jetlog](https://jetlog.app/import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222025-12-10%22%2C%22flight_number%22%3A%22KL1023%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%5D%7D%5D%2C%22people%22%3A%5B%5D%7D)

**Example response**
```json
{"data": "OK", "skipped": []}
```

Full worked examples of every `skipped`/`warnings` shape (all six skip reasons, plus the warnings array) live in EXAMPLES.md's ["Reading the API response"](EXAMPLES.md#reading-the-api-response) — every reason is asserted by the backend test suite.

## Tips
- Keep `ref_id` unique in `people`; reuse in `entries[*].people`.
- Use UTC for times; `date` is `YYYY-MM-DD`.
- Batch large external imports; split deeplinks if URLs get too long.
