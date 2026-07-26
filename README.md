# Jetlog Import Guide

Two ways to bring flights into Jetlog:
- **Deeplink (jetlog://import?data=…)** – for end users/scripts that can open the Jetlog app.
- **External Partner API (https://jetlog.app/external/v1/import)** – HTTP endpoint with dual-key auth (`Bearer <user_key>:<partner_key>`).

The **JSON payload is the same** for both flows (see “Payload schema” below).

Ready-to-use payloads, encoded deeplinks and curl calls: **[EXAMPLES.md](EXAMPLES.md)**.

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
| `type`                 | String | Yes      | Must be `"flight"`.                       |
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
| `takeoffs_and_landings`| Object | No       | `{ "takeoffs": n, "landings": n }` — send **both** counts. The API also accepts a day/night split (see its Behavior section); the deeplink does not. |
| `remarks`              | String | No       | Free text, max 1000 characters. **Never overwrites remarks the entry already has** — see the per-flow rules below. |
| `is_deleted`           | Bool   | No       | Soft-delete an entry this caller created. `false` restores one. |
| `update_flight_data`   | Bool   | No       | Auto-update from external sources (default: true). |

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

**Remarks are never silently overwritten**

Remarks are the pilot's own text, so an import can add them but not quietly replace them:

- **External Partner API** — write-once. Remarks are written whenever the entry has none, so you can add them on a later import of a flight you sent earlier without them. Once an entry *has* remarks they are never replaced — whoever wrote them, your own earlier import or the pilot in the app. A partner cannot correct its own earlier remark.
- **Deeplink** — the import preview shows the remarks change as `existing → new` before anything is written, and offers a **Replace / Add** choice on that row. `Add` keeps the stored note and appends the imported text after it; re-importing the same text twice does not stack it. When the entry has no remarks yet, the imported value is simply written and no choice is offered.

**Where the two flows differ**

Despite the shared payload, these differ — check them if you support both:

| | Deeplink | External Partner API |
| :-- | :-- | :-- |
| `people` top-level key | **Required** (omitting it fails the whole payload) | Optional |
| `type` on an entry | **Required** | Defaults to `"flight"` |
| Non-`"flight"` entries | Silently dropped | Reported in `skipped` as `unsupported_type` |
| Entry required fields | `flight_number` **or** `registration` | `from` **and** `to` |
| `takeoffs_and_landings` | `{takeoffs, landings}` only, both required | Also accepts the day/night split |
| `update_flight_data` when omitted | Inferred: `false` if any actual time is supplied, else `true` | Always defaults to `true` |
| `remarks` on a re-import | Replace / Add choice in the preview | Write-once; never overwritten |
| Unresolvable `people[].ref_id` | Kept for the import review to resolve | Dropped from the crew list |
| Matching an existing person | May update their `default_role`; also matches on a single name | Never modifies an existing person; matches `employee_number` then first+last only |

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
- Errors: invalid fields/refs may yield partial or failed imports.
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
- Soft-delete: `is_deleted: true` deletes only the caller’s own external entries. Sending `is_deleted: false` for the same flight restores one you previously deleted.
- Entries from another source (the app itself, a roster import, another partner) are never modified — they come back as `"duplicate"` in `skipped`.
- People:
  - A submitted person is matched against the people the user already has: first by `employee_number`, otherwise by `first_name` + `last_name` (ignoring case and surrounding whitespace).
  - **A matched person is reused but never modified.** The API will not rename an existing contact, change their `default_role`, or alter their `employee_number` — this includes the user's own profile. Only a person matching nothing is created, using every field supplied.
  - `SELF` = the authenticated user. A submitted person that matches the user's own profile resolves to it instead of creating a duplicate contact.
  - Two `ref_id`s resolving to the same person collapse to one crew assignment on an entry (the first `role` wins). A `ref_id` that resolves to nothing is dropped from the crew list.
  - Crew is merged, never replaced: omitting `people` — or sending `[]` — on a re-import keeps the existing crew. There is no way to remove crew from an entry via this API.
- Success: `{"data": "OK", "skipped": [...]}`; errors return `{"error": "<message>"}`.
- Skipped reasons:
  - `"duplicate"`: entry matches existing entry from a different source (fields: `date`, `flight_number`, `from`, `to`, `reason`).
  - `"missing_route"`: entry lacks `from` and `to` (fields: `date`, `flight_number`, `reason`).
  - `"unsupported_type"`: entry `type` is not `"flight"` (fields: `date`, `flight_number`, `type`, `reason`). Nothing is stored for it.
- Rows are independent: one skipped or rejected row does not prevent the rest of the payload from importing.

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
        "people":[{"ref_id":"SELF","role":"PIC"}],
        "takeoffs_and_landings":{"takeoffs":1,"landings":1}
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
    {"date": "2025-12-11", "flight_number": "KL2000", "reason": "missing_route"}
  ]
}
```

## Tips
- Keep `ref_id` unique in `people`; reuse in `entries[*].people`.
- Use UTC for times; `date` is `YYYY-MM-DD`.
- Batch large external imports; split deeplinks if URLs get too long.
