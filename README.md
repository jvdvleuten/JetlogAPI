# Jetlog Import Guide

Two ways to bring flights into Jetlog:
- **Deeplink (jetlog://import?data=…)** – for end users/scripts that can open the Jetlog app.
- **External Partner API (/external/v1/import)** – HTTP endpoint with dual-key auth (`Bearer <user_key>:<partner_key>`).

The **JSON payload is the same** for both flows (see “Payload schema” below).

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
| `scheduled_off_blocks` | String | No       | `HH:MM` zulu.                             |
| `registration`         | String | No       | Aircraft registration.                    |
| `from`                 | String | No       | ICAO departure.                           |
| `to`                   | String | No       | ICAO arrival.                             |
| `off_blocks`           | String | No       | `HH:MM` zulu.                             |
| `airborne`             | String | No       | `HH:MM` zulu.                             |
| `touchdown`            | String | No       | `HH:MM` zulu.                             |
| `on_blocks`            | String | No       | `HH:MM` zulu.                             |
| `people`               | Array  | No       | Crew list (see below).                    |
| `takeoffs_and_landings`| Object | No       | `{ "takeoffs": n, "landings": n }`.       |
| `is_deleted`           | Bool   | No       | For API: soft-delete caller’s own entry.  |

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
- If you include yourself in `people`, your details may be updated by the payload.

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
- Entry match: per user by `date + flight_number + entry_source` (set server-side to `external`); updates or creates accordingly.
- Soft-delete: `is_deleted: true` deletes only the caller’s own external entries.
- People: matched/created by refs/employee numbers; `SELF` = authenticated user.
- Aircraft fields are ignored here (we do not alter user aircraft via this API).
- Success: `{"data": "OK"}`; errors return `{"error": "<message>"}`.

**Example request**
```sh
curl -X POST https://api.your-jetlog-host/external/v1/import \
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

## Tips
- Keep `ref_id` unique in `people`; reuse in `entries[*].people`.
- Use UTC for times; `date` is `YYYY-MM-DD`.
- Batch large external imports; split deeplinks if URLs get too long.
