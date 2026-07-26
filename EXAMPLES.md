# Import Examples

Copy-paste examples for both import flows. Every payload below is valid for the
**External Partner API**; the ones marked *deeplink-safe* also work as a
`jetlog://import?data=…` link.

Two rules catch most mistakes:

- A **deeplink** requires the top-level `people` key (send `[]` if there is no
  crew) and requires `type` on every entry. The API defaults both.
- A **deeplink** entry needs `flight_number` **or** `registration`. An **API**
  entry needs `from` **and** `to`.

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

All entry fields both flows accept, including the planned times and remarks.

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

### Day/night takeoffs and landings — API only

The API accepts the split shape. **The deeplink rejects it** and only understands `{"takeoffs": n, "landings": n}`, so no deeplink is given here.

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
  {"date": "2026-08-16", "flight_number": "SIM1", "type": "fstd", "reason": "unsupported_type"}
]}
```

- `duplicate` — the flight already exists from another source (the app, a roster
  import, another partner). Those are never modified.
- `missing_route` — `from`/`to` were absent, which the API requires.
- `unsupported_type` — `type` was not `"flight"`. Carries `type` as well, and
  nothing is stored for that row.

Rows are independent: a skipped row does not stop the rest of the payload from
importing, so always read `skipped` rather than assuming a 200 means every row
landed. A malformed request that cannot be processed at all returns a non-200
with `{"error": "…"}` and writes nothing.

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
