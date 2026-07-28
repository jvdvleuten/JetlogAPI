# Import Examples

Copy-paste examples for both import flows. Every payload below is valid for the
**External Partner API**; the ones marked *deeplink-safe* also work as a
`jetlog://import?data=…` link.

One rule catches most mistakes:

- A **deeplink** entry needs `flight_number` **or** `registration`. An **API**
  entry needs `from` **and** `to`.

Everything else — the top-level `people` key, an entry's `type`, and the
takeoffs/landings shape — is optional/defaulted/tolerated the same way by both
flows now; see the README's schema table for specifics.

Times are `HH:MM` zulu relative to `date`. Dates are strictly `YYYY-MM-DD` —
`01-03-2026` is rejected by both flows.

---

### Minimal flight (deeplink-safe)

The smallest payload that satisfies both flows: identity for the deeplink, route for the API.

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

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-14%22%2C%22flight_number%22%3A%22KL1023%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL"}],"people":[]}'
```

### Every supported field (deeplink-safe)

All entry fields both flows accept, including the planned times and remarks. (`update_flight_data` is shown explicitly here; omitting it would infer the same `false` on both flows, because the payload carries actual times — see the field table in the README.)

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-14",
      "flight_number": "KL1023",
      "scheduled_off_blocks": "14:00",
      "scheduled_on_blocks": "15:10",
      "registration": "PH-BXD",
      "from": "EHAM",
      "to": "EGLL",
      "off_blocks": "14:08",
      "airborne": "14:28",
      "touchdown": "14:55",
      "on_blocks": "15:05",
      "takeoffs_and_landings": {
        "takeoffs": 1,
        "landings": 1
      },
      "remarks": "Line check. CAT II approach.",
      "update_flight_data": false,
      "people": [
        {
          "ref_id": "SELF",
          "role": "PIC"
        }
      ]
    }
  ],
  "people": []
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-14%22%2C%22flight_number%22%3A%22KL1023%22%2C%22scheduled_off_blocks%22%3A%2214%3A00%22%2C%22scheduled_on_blocks%22%3A%2215%3A10%22%2C%22registration%22%3A%22PH-BXD%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22off_blocks%22%3A%2214%3A08%22%2C%22airborne%22%3A%2214%3A28%22%2C%22touchdown%22%3A%2214%3A55%22%2C%22on_blocks%22%3A%2215%3A05%22%2C%22takeoffs_and_landings%22%3A%7B%22takeoffs%22%3A1%2C%22landings%22%3A1%7D%2C%22remarks%22%3A%22Line%20check.%20CAT%20II%20approach.%22%2C%22update_flight_data%22%3Afalse%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%5D%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","scheduled_off_blocks":"14:00","scheduled_on_blocks":"15:10","registration":"PH-BXD","from":"EHAM","to":"EGLL","off_blocks":"14:08","airborne":"14:28","touchdown":"14:55","on_blocks":"15:05","takeoffs_and_landings":{"takeoffs":1,"landings":1},"remarks":"Line check. CAT II approach.","update_flight_data":false,"people":[{"ref_id":"SELF","role":"PIC"}]}],"people":[]}'
```

### Flight with crew (deeplink-safe)

`ref_id` links the crew list to the people list and is not stored. `SELF` is you and needs no people entry.

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-15",
      "flight_number": "KL1024",
      "from": "EGLL",
      "to": "EHAM",
      "people": [
        {
          "ref_id": "SELF",
          "role": "PIC"
        },
        {
          "ref_id": "FO1",
          "role": "FO"
        },
        {
          "ref_id": "CA1",
          "role": "Purser"
        }
      ]
    }
  ],
  "people": [
    {
      "ref_id": "FO1",
      "first_name": "Fantas",
      "last_name": "Tico",
      "default_role": "FO",
      "employee_number": "00923"
    },
    {
      "ref_id": "CA1",
      "first_name": "Sally",
      "last_name": "Skyway",
      "default_role": "Purser",
      "employee_number": "01556"
    }
  ]
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-15%22%2C%22flight_number%22%3A%22KL1024%22%2C%22from%22%3A%22EGLL%22%2C%22to%22%3A%22EHAM%22%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%2C%7B%22ref_id%22%3A%22FO1%22%2C%22role%22%3A%22FO%22%7D%2C%7B%22ref_id%22%3A%22CA1%22%2C%22role%22%3A%22Purser%22%7D%5D%7D%5D%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22FO1%22%2C%22first_name%22%3A%22Fantas%22%2C%22last_name%22%3A%22Tico%22%2C%22default_role%22%3A%22FO%22%2C%22employee_number%22%3A%2200923%22%7D%2C%7B%22ref_id%22%3A%22CA1%22%2C%22first_name%22%3A%22Sally%22%2C%22last_name%22%3A%22Skyway%22%2C%22default_role%22%3A%22Purser%22%2C%22employee_number%22%3A%2201556%22%7D%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-15","flight_number":"KL1024","from":"EGLL","to":"EHAM","people":[{"ref_id":"SELF","role":"PIC"},{"ref_id":"FO1","role":"FO"},{"ref_id":"CA1","role":"Purser"}]}],"people":[{"ref_id":"FO1","first_name":"Fantas","last_name":"Tico","default_role":"FO","employee_number":"00923"},{"ref_id":"CA1","first_name":"Sally","last_name":"Skyway","default_role":"Purser","employee_number":"01556"}]}'
```

### Several flights in one call (deeplink-safe)

Entries are independent: one bad row is reported separately rather than losing the good ones (the API returns it under `skipped`).

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-16",
      "flight_number": "KL1601",
      "from": "EHAM",
      "to": "LEMD",
      "off_blocks": "07:05",
      "on_blocks": "09:40"
    },
    {
      "type": "flight",
      "date": "2026-08-16",
      "flight_number": "KL1602",
      "from": "LEMD",
      "to": "EHAM",
      "off_blocks": "10:25",
      "on_blocks": "13:00"
    }
  ],
  "people": []
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-16%22%2C%22flight_number%22%3A%22KL1601%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22LEMD%22%2C%22off_blocks%22%3A%2207%3A05%22%2C%22on_blocks%22%3A%2209%3A40%22%7D%2C%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-16%22%2C%22flight_number%22%3A%22KL1602%22%2C%22from%22%3A%22LEMD%22%2C%22to%22%3A%22EHAM%22%2C%22off_blocks%22%3A%2210%3A25%22%2C%22on_blocks%22%3A%2213%3A00%22%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-16","flight_number":"KL1601","from":"EHAM","to":"LEMD","off_blocks":"07:05","on_blocks":"09:40"},{"type":"flight","date":"2026-08-16","flight_number":"KL1602","from":"LEMD","to":"EHAM","off_blocks":"10:25","on_blocks":"13:00"}],"people":[]}'
```

### Adding remarks to a flight you already imported (deeplink-safe)

Re-send the same identity with remarks. The API stores remarks only on the entry it created, so this adds them if it created the flight and left them blank. In the app the import preview shows the change and offers **Replace / Add** when the entry already has remarks.

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-14",
      "flight_number": "KL1023",
      "from": "EHAM",
      "to": "EGLL",
      "remarks": "Diverted to EGKK for weather."
    }
  ],
  "people": []
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-14%22%2C%22flight_number%22%3A%22KL1023%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22remarks%22%3A%22Diverted%20to%20EGKK%20for%20weather.%22%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL","remarks":"Diverted to EGKK for weather."}],"people":[]}'
```

### Clearing a value you already imported (deeplink-safe)

Re-send the same identity with a field set to explicit `null` to clear it — the one case where `null` isn't the same as leaving the key out (see the README's "What a JSON `null` means depends on the field"). Only the 6 clearable value fields work this way: `off_blocks`, `airborne`, `touchdown`, `on_blocks`, `registration`, `takeoffs_and_landings`. `scheduled_off_blocks`/`scheduled_on_blocks` are not among them — a `null` there is treated as omitted, because the flight-data feed refills a nil scheduled column itself and neither field has a per-field timestamp for a clear to hold against.

Given an entry already imported with `"off_blocks": "07:05"`, this clears it:

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-16",
      "flight_number": "KL1601",
      "from": "EHAM",
      "to": "LEMD",
      "off_blocks": null
    }
  ],
  "people": []
}
```

Expected result: the matched entry's `off_blocks` clears to empty, exactly like the normal sync upsert — only that field's own edit timestamp is bumped, every other stored field (e.g. `on_blocks`) is untouched. On the API this syncs to other devices like any edit, and only ever lands on an entry this same partner imported. In the app, the deeplink's import preview shows the change as `"07:05" → "(empty)"` before anything is written.

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-16%22%2C%22flight_number%22%3A%22KL1601%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22LEMD%22%2C%22off_blocks%22%3Anull%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-16","flight_number":"KL1601","from":"EHAM","to":"LEMD","off_blocks":null}],"people":[]}'
```

### Deleting a flight you imported (deeplink-safe)

Only ever affects an entry this caller created. Send `"is_deleted": false` with the same identity to restore it.

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-14",
      "flight_number": "KL1023",
      "from": "EHAM",
      "to": "EGLL",
      "is_deleted": true
    }
  ],
  "people": []
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-14%22%2C%22flight_number%22%3A%22KL1023%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22is_deleted%22%3Atrue%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL","is_deleted":true}],"people":[]}'
```

### Day/night takeoffs and landings (deeplink-safe)

Both flows accept the split shape, in addition to the plain `{"takeoffs": n, "landings": n}` counts shown earlier — send whichever matches how you track landings.

The `"type"` key inside `takeoffs_and_landings` is optional, and both flows resolve it the same way: an explicit `"type"` (e.g. `"manual"`) is honored and short-circuits inference. When it's absent, both flows infer instead — checking the plain `takeoffs`/`landings` counts first, and only falling back to the day/night counts if those aren't present. An empty `takeoffs_and_landings: {}` is ignored silently either way: no error, no counts recorded. An explicit `"type"` that isn't `"auto"` or `"manual"` is rejected — the API skips the whole row as `"invalid_field"`, while the deeplink imports the entry, drops just the counts, and flags the invalid type as a per-row error in the import preview (see the flow-differences table in the README).

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2026-08-17",
      "flight_number": "KL1701",
      "from": "EHAM",
      "to": "LTFM",
      "takeoffs_and_landings": {
        "type": "manual",
        "takeoffs_day": 1,
        "takeoffs_night": 0,
        "landings_day": 0,
        "landings_night": 1
      }
    }
  ],
  "people": []
}
```

**Deeplink**

```
jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222026-08-17%22%2C%22flight_number%22%3A%22KL1701%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22LTFM%22%2C%22takeoffs_and_landings%22%3A%7B%22type%22%3A%22manual%22%2C%22takeoffs_day%22%3A1%2C%22takeoffs_night%22%3A0%2C%22landings_day%22%3A0%2C%22landings_night%22%3A1%7D%7D%5D%2C%22people%22%3A%5B%5D%7D
```

**API**

```sh
curl -X POST https://jetlog.app/external/v1/import \
  -H "Authorization: Bearer $USER_KEY:$PARTNER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-17","flight_number":"KL1701","from":"EHAM","to":"LTFM","takeoffs_and_landings":{"type":"manual","takeoffs_day":1,"takeoffs_night":0,"landings_day":0,"landings_night":1}}],"people":[]}'
```

### IATA codes

Three-letter codes are converted when recognised, so this stores `EHAM` → `WMKK`:

```json
{"entries":[{"type":"flight","date":"2026-08-18","flight_number":"KL809","from":"AMS","to":"KUL"}],"people":[]}
```

An unrecognised three-letter code is stored verbatim, with no error — check the
result if you rely on the conversion.

---

## Reading the API response

```json
{"data": "OK", "skipped": []}
```

`skipped` lists rows that were accepted but not written:

```json
{"data": "OK", "skipped": [
  {"date": "2026-08-14", "flight_number": "KL1023", "from": "EHAM", "to": "EGLL", "reason": "duplicate"},
  {"date": "2026-08-15", "flight_number": "KL2000", "reason": "missing_route"},
  {"date": "2026-08-16", "flight_number": "SIM1", "type": "fstd", "reason": "unsupported_type"},
  {"date": "2026-08-17", "flight_number": "KL1701", "from": "EHAM", "to": "LTFM", "reason": "duplicate_in_payload"},
  {"date": "2026-08-18", "flight_number": "KL1801", "reason": "invalid_field", "fields": ["off_blocks"]},
  {"date": "2026-08-19", "flight_number": "KL1802", "reason": "invalid_field", "fields": ["takeoffs_and_landings.landings"]}
]}
```

- `duplicate` — the flight already exists from another source (the app, a roster
  import, another partner). Those are never modified.
- `missing_route` — `from`/`to` were absent, which the API requires.
- `unsupported_type` — `type` was not `"flight"`. Carries `type` as well, and
  nothing is stored for that row.
- `duplicate_in_payload` — this same `(date, flight_number, from, to)` identity
  appeared more than once in this request; the **last** occurrence was
  imported and the earlier one(s) are reported this way.
- `deleted` — a same-source entry with this identity exists but is
  soft-deleted, and this row said nothing about `is_deleted`. Send
  `is_deleted: false` with the same identity to restore it instead of
  resending the row as-is.
- `invalid_field` — the row failed the same field-level validation a direct
  write would (an unparsable time, an incomplete `takeoffs_and_landings`
  pair, ...); `fields` names what failed. Only this row is skipped, the rest
  of the batch still imports. A field inside an embedded object is dotted —
  `"takeoffs_and_landings.landings"`, not just `"landings"`.

A soft-deleted entry doesn't lock out a re-import forever, either: it only
reserves the identity for *its own* source. If a flight you deleted is
re-imported by a different source (the app itself, a roster import, another
partner), that import creates a new, live row alongside your deleted one
rather than reviving or merging into it.

An entry can import successfully and still be worth a second look: a
`"warnings"` array rides alongside (never instead of) `skipped` whenever
there's something to flag —

```json
{"data": "OK", "skipped": [], "warnings": [
  {"date": "2026-08-19", "flight_number": "KL1901", "ref_id": "GHOST", "reason": "unresolved_person_ref"}
]}
```

- `unresolved_person_ref` — a crew member's `ref_id` didn't resolve to a known
  person. The flight still imports, just without that crew member.

Rows are independent: a skipped row does not stop the rest of the payload from
importing, so always read `skipped` (and `warnings`) rather than assuming a 200
means every row landed exactly as sent. A malformed request that cannot be
processed at all returns a non-200 with `{"error": "…"}` — always a short,
stable string, never a raw changeset or internal id. That non-200 does **not**
guarantee nothing was written, though: `people` and `entries` are committed in
separate transactions, people first, so a batch that later fails while
processing `entries` can still leave newly-created `people` rows behind. It's
safe to resend the same payload — those people will match on the retry
instead of being duplicated.

---

## Building a deeplink yourself

The `data` parameter is the URL-encoded JSON string:

```sh
python3 -c '
import json, urllib.parse
payload = {"entries": [{"type": "flight", "date": "2026-08-14", "flight_number": "KL1023",
                        "from": "EHAM", "to": "EGLL"}], "people": []}
print("jetlog://import?data=" + urllib.parse.quote(json.dumps(payload, separators=(",", ":")), safe=""))
'
```

Split very large payloads across several links — URLs have length limits the API
does not.
