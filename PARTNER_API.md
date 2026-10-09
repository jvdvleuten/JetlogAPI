# Partner API reference

This is the reference for everything an app can call once a pilot has connected it to their Jetlog logbook. The [README](README.md) describes the payload of the import route. [MIGRATION.md](MIGRATION.md) covers the connection itself: the metadata document, the authorization request, the token exchange and refreshing. This page covers what a connected app can do with its token, route by route.

Words used on this page:

- A **partner** is an app or service that works on behalf of pilots.
- A **pilot** is the person whose logbook it is.
- The **token route** is the import route, `POST /api/partner/v1/import`.
- The **read routes** and the **proposal routes** are the other routes listed under [The routes](#the-routes).

To see the whole flow work before you build anything, run the [sample app](#the-sample-app).

Sections:

1. [Access levels](#access-levels)
2. [Asking for a level](#asking-for-a-level)
3. [The routes](#the-routes)
4. [Calling the routes](#calling-the-routes)
5. [Reading the logbook](#reading-the-logbook)
6. [Proposing changes](#proposing-changes)
7. [The operations format](#the-operations-format)
8. [Errors per route](#errors-per-route)
9. [Limits](#limits)
10. [What an app can never do](#what-an-app-can-never-do)
11. [The sample app](#the-sample-app)

## Access levels

A pilot connects a partner at one of two levels. The pilot chooses when approving the connection in the Jetlog app.

| Level | Scope in the token | What the app can do |
| :-- | :-- | :-- |
| Own flights | `import` | Add flights with their crew, and change or remove the flights it added, through the import route. Nothing else. |
| Whole logbook | `import read write` | Everything the own flights level can do. It can also read the whole logbook, and propose changes to anything in it. A proposal changes nothing until the pilot approves it in the Jetlog app. |

The three scopes mean this:

- `import` is the direct import of the app's own flights through the token route.
- `read` is reading the logbook through the read routes.
- `write` is proposing changes. It never applies them.

Flights an app adds through the import route are written directly at both levels, and the app changes or removes those through the import route as well. At the whole logbook level, a change to anything the app did not add goes through a proposal. Whatever an app sends, it cannot change a flight it did not add unless the pilot approves that change.

The pilot can always grant the lower level when the wider one was asked. The pilot can also remove the app at any time under Settings > Connected Apps, which ends the connection.

## Asking for a level

The level is requested with the `scope` parameter of the authorization request, which [MIGRATION.md](MIGRATION.md#3-build-the-authorization-request) describes in full.

- `scope=import` asks for own flights. The pilot is not offered a choice, and the token carries exactly `import`.
- `scope=import read write` asks for the whole logbook and lets the pilot choose between the two levels.
- A request that does not contain both `read` and `write` is handled as `import`.

Whether an app may ask for the whole logbook is set by Jetlog for each app. Say that you want it when you send the URL of your metadata document to support@jetlog.app, or write later to have it enabled. An app that is not enabled is offered the own flights level only, whatever it asks for.

An app can therefore receive less than it asked for. The token response tells what was granted, in its `scope` field:

```json
{
  "access_token": "jlp_example_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "jlr_example_refresh_token",
  "scope": "import read write"
}
```

When the pilot picks own flights, or the app is not enabled for the whole logbook, the same response says `"scope": "import"`. Read `scope` from the token response and not from your own request. When `read` or `write` is missing, do not call the read routes or the proposal routes. They answer `403` with `insufficient_scope`.

A refresh keeps the level that was granted. To get another level, send the pilot through the authorization request again.

A request for the whole logbook looks like this. It is the request from MIGRATION.md with a different `scope`:

```sh
AUTH_URL="https://jetlog.app/oauth/authorize?response_type=code&client_id=https%3A%2F%2Fpartner.example.com%2Fjetlog-client.json&redirect_uri=https%3A%2F%2Fpartner.example.com%2Foauth%2Fjetlog%2Fcallback&scope=import%20read%20write&state=${STATE}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&resource=https%3A%2F%2Fjetlog.app%2Fapi%2Fpartner%2Fv1"
open "$AUTH_URL"    # macOS. On Linux use xdg-open.
```

What the pilot sees when you ask for the whole logbook:

- The Jetlog app shows your name and a choice between "Only its own flights" and "My whole logbook", each with a sentence on what it means. The wider choice is never preselected.
- The page used when a pilot signs in with an email code instead of the app offers the same choice.
- Approving at this level needs a current version of the Jetlog app.
- Afterwards, Settings > Connected Apps shows the level the pilot chose.

When you ask for `import`, the pilot sees the screen described in [MIGRATION.md](MIGRATION.md#what-the-pilot-sees-on-the-same-phone), and nothing changes for you.

If Jetlog later switches the whole logbook level off for an app, the tokens that hold it lose the read routes and the proposal routes at once. Those routes answer `403` with `insufficient_access`. Their import route keeps working.

## The routes

All routes live under `https://jetlog.app/api/partner/v1`.

| Method and path | Needs | What it does |
| :-- | :-- | :-- |
| `POST /import` | `import` | Adds flights, and changes or removes the flights the app added. See the [README](README.md#external-partner-api). |
| `GET /me` | `read` | Who the pilot is. |
| `GET /entries` | `read` | Lists the pilot's flights, with filters and paging. |
| `GET /entries/:id` | `read` | One flight. |
| `GET /people` | `read` | The pilot's crew list. |
| `GET /aircraft` | `read` | The pilot's aircraft. |
| `GET /totals` | `read` | The pilot's flight time totals. |
| `POST /changes` | `write` | Proposes changes. Writes nothing. |
| `GET /changes/:id` | `write` | The status of a proposal this connection made. |

## Calling the routes

Send `Authorization: Bearer <access_token>` with the access token of the pilot you act for. Requests and responses are JSON, so send `Content-Type: application/json` with a body. Ids are UUIDs, dates are `YYYY-MM-DD` and times are `HH:MM` zulu.

A partner token works on these routes only. Every other Jetlog route refuses it.

Every route can answer these:

| Status | Body | Meaning |
| :-- | :-- | :-- |
| `401` | `{"error":"invalid_token"}` and `WWW-Authenticate: Bearer error="invalid_token"` | The token is missing, unknown, expired, revoked, or meant for another resource. Refresh it once. If that fails, the pilot connects again. |
| `403` | `{"error":"integration_disabled"}` | Jetlog has switched your partner registration off. |
| `403` | `{"error":"insufficient_scope"}` | The token does not carry the scope the route needs. |
| `403` | `{"error":"insufficient_access"}` | The read routes and proposal routes only. Jetlog has switched the whole logbook level off for your app. |
| `429` | A `Retry-After` header, in seconds, and `{"error":"rate_limited","retry_after":n}` | Too many requests for this pilot. Wait, then send the same request. |

The sections below add the errors that belong to one route. [Errors per route](#errors-per-route) has them all in one table.

## Reading the logbook

The read routes need the `read` scope. They only read. They return what Jetlog stores for the pilot, with the same field names the Jetlog app uses.

Files, photos and signature images can never be read by an app. The responses only say whether a signature or a photo exists.

### GET /me

Who the pilot is. `user_id` is the pilot's id. `self_person_id` is the id the pilot has as a crew member, which is what the `people` of a flight use for the pilot themselves. The body can carry further account fields. Ignore the ones you do not know.

```sh
curl -sS https://jetlog.app/api/partner/v1/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "user_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10",
  "self_person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10"
}
```

### GET /entries

Lists flights and simulator sessions, oldest first, by the date they took place and then by id.

| Parameter | Meaning |
| :-- | :-- |
| `from`, `to` | First and last date to include, `YYYY-MM-DD`. They compare with the date the flight took place, which is `derived.date` in the response. |
| `type` | `flight` or `fstd`. Without it both come back. `fstd` is a simulator session. |
| `registration` | Registration as Jetlog stores it, uppercase without separators, for example `PHBXD`. |
| `airport` | An airport code, ICAO or IATA. It matches flights that departed from or arrived at that airport. |
| `flight_number` | A flight number. The match ignores case. |
| `person_id` | Only flights with this crew member. Take the id from `GET /people`. |
| `role` | Only together with `person_id`. Only flights where that crew member had this role. |
| `include_deleted` | `true` also returns removed flights, which have `is_deleted` set to `true`. The default is `false`. |
| `limit` | Flights per page. The default is 50 and the maximum is 200. |
| `after_date`, `after_id` | Where the next page starts. Send both, copied from `pagination.next_cursor` of the previous page. |

```sh
curl -sS "https://jetlog.app/api/partner/v1/entries?from=2026-08-01&to=2026-08-31&airport=EHAM&limit=1" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "entries": [
    {
      "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
      "version": 412,
      "type": "flight",
      "date": "2026-08-14",
      "entry_source": "manual",
      "flight_number": "KL1023",
      "registration": "PHBXD",
      "from": "EHAM",
      "to": "EGLL",
      "actual_from": null,
      "actual_to": null,
      "off_blocks": "14:08:00",
      "airborne": "14:28:00",
      "touchdown": "14:55:00",
      "on_blocks": "15:05:00",
      "registration_system": null,
      "off_blocks_system": null,
      "airborne_system": null,
      "touchdown_system": null,
      "on_blocks_system": null,
      "system_date": null,
      "system_from": null,
      "system_to": null,
      "update_flight_data": false,
      "derived": {
        "date": "2026-08-14",
        "registration": "PHBXD",
        "from": "EHAM",
        "to": "EGLL",
        "off_blocks": "14:08:00",
        "airborne": "14:28:00",
        "touchdown": "14:55:00",
        "on_blocks": "15:05:00"
      },
      "ifr": true,
      "is_completed": true,
      "is_bulk": false,
      "manual_times": false,
      "aircraft_icao_code": "B738",
      "takeoffs_and_landings": {
        "type": "auto",
        "takeoffs": 1,
        "landings": 1,
        "takeoffs_day": null,
        "takeoffs_night": null,
        "landings_day": null,
        "landings_night": null
      },
      "approaches": [],
      "go_arounds": 0,
      "passengers_on_board": 142,
      "fuel_planned": 5200,
      "fuel_used": 4980,
      "cargo_on_board": null,
      "start_time": null,
      "end_time": null,
      "fstd_id": null,
      "session_type": null,
      "fstd_takeoffs": null,
      "fstd_landings": null,
      "is_imported_from_other_logbook": false,
      "is_deleted": false,
      "remarks": null,
      "people": [
        {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "role": "PIC", "is_deleted": false}
      ],
      "updated_at": "2026-08-14T15:42:07.318204Z",
      "calculated_times": null,
      "signature": "none",
      "signature_attachment_id": null,
      "attachment_count": 0
    }
  ],
  "pagination": {
    "limit": 1,
    "has_more": true,
    "next_cursor": {"date": "2026-08-14", "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01"}
  }
}
```

Reading a flight:

- `derived` holds the values to show a pilot. While `update_flight_data` is `true`, Jetlog fills the actual times, the registration and the airports from its flight tracking, and `derived` shows those. Otherwise `derived` shows what the pilot or an app entered. The plain fields and the `_system` fields are the two sources it chooses from.
- `entry_source` says where the flight came from: `manual` for a flight the pilot entered, `external:` followed by a short name for a flight a partner added, and other values for roster imports and AI assistants.
- `version` and `updated_at` change whenever the flight changes.
- `people` lists the crew. Each `person_id` is an id from `GET /people`. The pilot's own id is `self_person_id`.
- `signature` is `none`, `waived` or `signed`. `attachment_count` is the number of files on the flight. The files and the signature image themselves cannot be reached.
- `calculated_times` is `null` while Jetlog has not calculated the flight yet. Otherwise it holds whole minutes per figure, with the same figure names as `totals` below, plus `cross_country_distance` and `computed_at`.
- Removed flights are left out unless you ask for them.

To read the next page, send the cursor back:

```sh
curl -sS "https://jetlog.app/api/partner/v1/entries?from=2026-08-01&to=2026-08-31&airport=EHAM&limit=1&after_date=2026-08-14&after_id=c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Keep the other parameters the same. The last page has `"has_more": false` and `"next_cursor": null`.

Errors: `400` with `{"error":"invalid_date"}` for a `from`, `to` or `after_date` that is not a date, `{"error":"invalid_type"}` for a `type` that is not `flight` or `fstd`, and `{"error":"invalid_parameter"}` for a `limit` that is not a number or an `include_deleted` that is not `true` or `false`.

### GET /entries/:id

One flight. The answer is `{"entry": {...}}`. The flight has the same fields as a row of the list above, plus `signature_sha256`. An id that does not exist, belongs to another pilot or was removed answers `404` with `{"error":"not_found"}`.

```sh
curl -sS https://jetlog.app/api/partner/v1/entries/a8d3f1c2-5e7b-4a9d-b6c4-2f1e0d9c8b7a \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

This flight was added by a partner, with Jetlog's flight tracking on:

```json
{
  "entry": {
    "id": "a8d3f1c2-5e7b-4a9d-b6c4-2f1e0d9c8b7a",
    "version": 538,
    "type": "flight",
    "date": "2026-09-02",
    "entry_source": "external:example-partner",
    "flight_number": "KL1001",
    "registration": "PHBXF",
    "from": "EHAM",
    "to": "LEMD",
    "actual_from": null,
    "actual_to": null,
    "off_blocks": null,
    "airborne": null,
    "touchdown": null,
    "on_blocks": null,
    "registration_system": "PHBXF",
    "off_blocks_system": "06:41:00",
    "airborne_system": "06:58:00",
    "touchdown_system": "08:41:00",
    "on_blocks_system": "08:52:00",
    "system_date": "2026-09-02",
    "system_from": "EHAM",
    "system_to": "LEMD",
    "update_flight_data": true,
    "derived": {
      "date": "2026-09-02",
      "registration": "PHBXF",
      "from": "EHAM",
      "to": "LEMD",
      "off_blocks": "06:41:00",
      "airborne": "06:58:00",
      "touchdown": "08:41:00",
      "on_blocks": "08:52:00"
    },
    "ifr": true,
    "is_completed": true,
    "is_bulk": false,
    "manual_times": false,
    "aircraft_icao_code": "B738",
    "takeoffs_and_landings": {
      "type": "auto",
      "takeoffs": 1,
      "landings": 1,
      "takeoffs_day": null,
      "takeoffs_night": null,
      "landings_day": null,
      "landings_night": null
    },
    "approaches": [
      {"type": "ils_cat1", "count": 1, "autolands": null}
    ],
    "go_arounds": 0,
    "passengers_on_board": 156,
    "fuel_planned": 6100,
    "fuel_used": 5870,
    "cargo_on_board": null,
    "start_time": null,
    "end_time": null,
    "fstd_id": null,
    "session_type": null,
    "fstd_takeoffs": null,
    "fstd_landings": null,
    "is_imported_from_other_logbook": false,
    "is_deleted": false,
    "remarks": "Late inbound crew",
    "people": [
      {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "role": "PIC", "is_deleted": false},
      {"person_id": "4d6e8a21-95f3-4b7c-a1d2-3e5f60718293", "role": "FO", "is_deleted": false}
    ],
    "updated_at": "2026-09-02T09:15:03.482911Z",
    "calculated_times": {
      "pilot_in_command_role": 131,
      "spic_role": null,
      "picus_role": null,
      "line_check_airman_role": null,
      "line_check_airman_initial_role": null,
      "senior_instructor_pic_role": null,
      "senior_instructor_co_pilot_role": null,
      "senior_instructor_observer_role": null,
      "dead_head_role": null,
      "route_instructor_role": null,
      "route_instructor_co_pilot_role": null,
      "co_pilot_role": null,
      "cruise_relief_raw_block": null,
      "cruise_relief_co_pilot_credited": null,
      "dual_role": null,
      "flight_instructor_role": null,
      "flight_examiner_role": null,
      "single_pilot_single_engine": null,
      "single_pilot_multi_engine": null,
      "multi_pilot": 131,
      "night": null,
      "ifr": 131,
      "cross_country": 131,
      "total_time_of_flight": 131,
      "total_air_time": 163,
      "fstd_session": null,
      "fstd_instructor_time": null,
      "fstd_examiner_time": null,
      "fstd_senior_instructor_time": null,
      "cross_country_distance": true,
      "computed_at": "2026-09-02T09:15:04Z"
    },
    "signature": "none",
    "signature_attachment_id": null,
    "attachment_count": 0,
    "signature_sha256": null
  }
}
```

### GET /people

The pilot's whole crew list, in one response without paging. Removed people are left out. The pilot's own row, which has the id `self_person_id`, is among them once it exists.

```sh
curl -sS https://jetlog.app/api/partner/v1/people \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "people": [
    {
      "id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10",
      "first_name": "Sam",
      "last_name": "Jansen",
      "default_role": "PIC",
      "employee_number": "10432",
      "is_imported_from_other_logbook": false,
      "has_photo": false
    },
    {
      "id": "4d6e8a21-95f3-4b7c-a1d2-3e5f60718293",
      "first_name": "Anna",
      "last_name": "de Vries",
      "default_role": "FO",
      "employee_number": null,
      "is_imported_from_other_logbook": false,
      "has_photo": false
    }
  ]
}
```

### GET /aircraft

The pilot's aircraft, in one response without paging. Removed aircraft are left out. The `id` is the registration as Jetlog stores it, which is what `registration` on a flight refers to. `aircraft_icao_code` and `aircraft_iata_code` are the type codes the pilot entered, `system_aircraft_icao_code` and `system_aircraft_iata_code` are the ones Jetlog looked up, and `use_system` says which of the two counts.

```sh
curl -sS https://jetlog.app/api/partner/v1/aircraft \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "aircraft": [
    {
      "id": "PHBXD",
      "use_system": true,
      "aircraft_icao_code": null,
      "aircraft_iata_code": null,
      "system_aircraft_icao_code": "B738",
      "system_aircraft_iata_code": "738",
      "is_imported_from_other_logbook": false
    }
  ]
}
```

### GET /totals

The pilot's flight time totals, in whole minutes, for the flights between `from` and `to`. Both are `YYYY-MM-DD`, both are included, and without them the totals cover the whole logbook. A figure is `null` when no flight in the range contributed to it. The object has one figure for every kind of time Jetlog calculates, and the example shows a selection.

```sh
curl -sS "https://jetlog.app/api/partner/v1/totals?from=2026-01-01&to=2026-12-31" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```json
{
  "totals": {
    "total_time_of_flight": 5421,
    "total_air_time": 4987,
    "pilot_in_command_role": 3180,
    "co_pilot_role": 2241,
    "multi_pilot": 5421,
    "night": 1204,
    "ifr": 5102,
    "taxi_time_minutes": 434,
    "command_pic_minutes": 3180,
    "entry_count": 61
  },
  "coverage": {
    "total": 61,
    "computed": 61,
    "pending": 0,
    "failed": 0
  }
}
```

The totals add up the calculated times Jetlog has stored for the flights. `coverage` tells whether that covers every flight in the range. `total` is the number of flights in the range, `computed` the ones with calculated times, `pending` the ones still waiting for their calculation, and `failed` the ones Jetlog could not calculate. While `pending` is above zero the totals can be short. A `from` or `to` that is not a date answers `400` with `{"error":"invalid_date"}`.

## Proposing changes

A proposal asks the pilot to change something in the logbook. The app sends it, Jetlog checks it without writing anything, and the pilot decides in the Jetlog app. Only the pilot can apply a proposal. Proposing needs the `write` scope.

### The flow end to end

1. The app sends `POST /changes` with a summary and a list of operations. Jetlog checks every operation against the logbook as it is now and stores the proposal with the status `pending`. Nothing in the logbook changes.
2. Jetlog notifies the pilot. The notification names your app and says how many flights it wants to change. Jetlog writes that text itself from the proposal, and the summary you send is not part of it. The proposal also waits in the pilot's list of changes to review in the Jetlog app.
3. The pilot opens the proposal in the Jetlog app and sees what every operation would change, before and after. The pilot approves all of it, approves only some of the operations, or rejects it. Reviewing a proposal needs a current version of the Jetlog app.
4. The app asks `GET /changes/:id` for the status, at a calm pace such as once a minute, until the status is no longer `pending`. The pilot decides at their own speed.
5. When the pilot approved, the changes are in the logbook. The pilot can still undo an approved change in the Jetlog app.

A proposal that nobody decides expires 24 hours after it was made. A pilot can have 20 open proposals at a time, counting the proposals of all apps and assistants together. A proposal holds up to 200 operations.

Every `POST /changes` makes a new proposal. After a timeout, do not send the same request again without thinking: the pilot would be asked about the same change twice. There is no route to list proposals, so keep the `id` from the answer.

A proposal belongs to the connection that made it, and it stays reachable across token refreshes. After a pilot disconnects your app and connects it again, the new connection cannot read the proposals of the old one.

### POST /changes

Needs `write`. The body has two fields:

| Field | Meaning |
| :-- | :-- |
| `summary` | A short sentence describing the whole change. Plain text, at most 500 characters, and longer text is shortened. It is required. The pilot sees it with the proposal. |
| `operations` | The changes, from 1 to 200 of them. [The operations format](#the-operations-format) describes them. |

This proposal corrects the registration on one flight:

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/changes \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Correct the registration of KL1023 on 14 August",
    "operations": [
      {
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {"registration": "PHBXE"}
      }
    ]
  }'
```

The answer is `201` with the proposal:

```json
{
  "pending_change": {
    "id": "0b9f3c7e-62a1-4e58-8d0c-71f4a2b6c5d3",
    "status": "pending",
    "client_kind": "partner",
    "client_name": "Example Partner",
    "summary": "Correct the registration of KL1023 on 14 August",
    "operations": [
      {
        "index": 0,
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {"registration": "PHBXE"}
      }
    ],
    "preview": [
      {
        "index": 0,
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "before": {
          "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
          "type": "flight",
          "flight_number": "KL1023",
          "date": "2026-08-14",
          "registration": "PHBXD",
          "from": "EHAM",
          "to": "EGLL",
          "off_blocks": "14:08:00",
          "airborne": "14:28:00",
          "touchdown": "14:55:00",
          "on_blocks": "15:05:00",
          "remarks": null,
          "signature": "none",
          "is_deleted": false,
          "people": [
            {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "name": "Sam Jansen", "role": "PIC", "is_self": true}
          ]
        },
        "after": {
          "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
          "type": "flight",
          "flight_number": "KL1023",
          "date": "2026-08-14",
          "registration": "PHBXE",
          "from": "EHAM",
          "to": "EGLL",
          "off_blocks": "14:08:00",
          "airborne": "14:28:00",
          "touchdown": "14:55:00",
          "on_blocks": "15:05:00",
          "remarks": null,
          "signature": "none",
          "is_deleted": false,
          "people": [
            {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "name": "Sam Jansen", "role": "PIC", "is_self": true}
          ]
        },
        "changed_fields": ["registration"]
      }
    ],
    "counts": {"creates": 0, "updates": 1, "deletes": 0},
    "error": null,
    "expires_at": "2026-10-10T09:12:44.512345Z",
    "decided_at": null,
    "applied_batch_id": null,
    "reverted_indices": [],
    "created_at": "2026-10-09T09:12:44.512345Z"
  }
}
```

The fields of a proposal:

| Field | Meaning |
| :-- | :-- |
| `id` | The id to poll. |
| `status` | One of the [statuses](#statuses). A new proposal is `pending`. |
| `client_kind` | `partner` for every proposal an app makes. |
| `client_name` | The name Jetlog registered for your app. |
| `summary` | Your summary, cleaned of control characters and extra white space. |
| `operations` | Your operations as Jetlog stored them. Each one has an `index` that counts from 0, and every create has an `id`. |
| `preview` | One item per operation, with the flight, person or other record `before` and `after`, and the `changed_fields`. This is what the pilot reviews. A create has `null` for `before`, and a delete shows `is_deleted` going to `true` in `after`. Each item also has `raw_before`, the previous values in the form Jetlog stores them for undoing a change. The example leaves it out, and an app does not need it. |
| `counts` | How many operations create, update and delete. After a partial approval it counts what was applied. |
| `error` | A short reason when the status is `failed`, and `null` otherwise. |
| `expires_at` | 24 hours after `created_at`. |
| `decided_at` | When the pilot approved or rejected it, or when it expired. `null` while it is pending. |
| `applied_batch_id` | Jetlog's id of the write after an approval, and `null` before. An app does not need it. |
| `reverted_indices` | The `index` of every operation the pilot undid after approving. Empty otherwise. |
| `created_at` | When the proposal was made. |

Errors of this route are in [Errors per route](#errors-per-route).

### GET /changes/:id

Needs `write`. The status of a proposal this connection made, as the same `pending_change` object. The id of a proposal that does not exist, or that another connection made, answers `404`.

```sh
curl -sS https://jetlog.app/api/partner/v1/changes/0b9f3c7e-62a1-4e58-8d0c-71f4a2b6c5d3 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

This is the same proposal after the pilot approved it:

```json
{
  "pending_change": {
    "id": "0b9f3c7e-62a1-4e58-8d0c-71f4a2b6c5d3",
    "status": "applied",
    "client_kind": "partner",
    "client_name": "Example Partner",
    "summary": "Correct the registration of KL1023 on 14 August",
    "operations": [
      {
        "index": 0,
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {"registration": "PHBXE"}
      }
    ],
    "preview": [
      {
        "index": 0,
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "before": {
          "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
          "type": "flight",
          "flight_number": "KL1023",
          "date": "2026-08-14",
          "registration": "PHBXD",
          "from": "EHAM",
          "to": "EGLL",
          "off_blocks": "14:08:00",
          "airborne": "14:28:00",
          "touchdown": "14:55:00",
          "on_blocks": "15:05:00",
          "remarks": null,
          "signature": "none",
          "is_deleted": false,
          "people": [
            {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "name": "Sam Jansen", "role": "PIC", "is_self": true}
          ]
        },
        "after": {
          "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
          "type": "flight",
          "flight_number": "KL1023",
          "date": "2026-08-14",
          "registration": "PHBXE",
          "from": "EHAM",
          "to": "EGLL",
          "off_blocks": "14:08:00",
          "airborne": "14:28:00",
          "touchdown": "14:55:00",
          "on_blocks": "15:05:00",
          "remarks": null,
          "signature": "none",
          "is_deleted": false,
          "people": [
            {"person_id": "7b1d1f5c-3a2e-4c8e-9d64-0f6a2b9c1e10", "name": "Sam Jansen", "role": "PIC", "is_self": true}
          ]
        },
        "changed_fields": ["registration"]
      }
    ],
    "counts": {"creates": 0, "updates": 1, "deletes": 0},
    "error": null,
    "expires_at": "2026-10-10T09:12:44.512345Z",
    "decided_at": "2026-10-09T09:31:02.118233Z",
    "applied_batch_id": "5e8c1a47-3b90-4f6d-a2c8-91d7e0b4f356",
    "reverted_indices": [],
    "created_at": "2026-10-09T09:12:44.512345Z"
  }
}
```

### Statuses

| Status | Meaning |
| :-- | :-- |
| `pending` | Waiting for the pilot. |
| `applied` | The pilot approved it, in full or in part, and the changes are made. |
| `rejected` | The pilot rejected it. Nothing was changed. |
| `expired` | Nobody decided within 24 hours. Nothing was changed. |
| `stale` | When the pilot approved, a flight or person the proposal touches had changed since it was proposed. Nothing was changed. The proposal stays open until it expires or the pilot rejects it, and it still counts as open. Send a new proposal built from current data. |
| `failed` | Applying it did not work, for example because a flight it touches was removed in the meantime. Nothing was changed. `error` holds a short reason. |
| `revoked` | The connection that made the proposal ended before the pilot decided, because the pilot removed the app or the refresh token was revoked. Nothing was changed. A new connection cannot read the proposals of an earlier one, so an app normally never sees this status. |

Poll until the status is no longer `pending`. Every other status is final, except `stale`, which stays open until the pilot rejects it or the 24 hours pass.

### Partial approval

The pilot may approve only some of the operations of a proposal. The operations that were left out are not applied and are not offered again. The status is `applied`, and `counts` describes only what was applied. Read the flights again to see what changed. To propose the rest again, send a new proposal.

Operations that depend on each other can only be approved together. A flight that lists a crew member created in the same proposal needs the operation that creates that person.

### After approval

The pilot can undo an approved change in the Jetlog app. The status then stays `applied`, and `reverted_indices` lists the operations that were undone. Flights an app creates through an approved proposal carry the same `entry_source` as the flights it imports, so they are the app's own flights afterwards and the app can change them through the import route.

## The operations format

An operation describes one change to one record.

| Field | Meaning |
| :-- | :-- |
| `op` | `create`, `update` or `delete`. |
| `resource` | `entry` for a flight, or `person` for a crew member. Other resources are not part of the partner API. |
| `id` | The id of the flight or person. Required for `update` and `delete`. Optional for `create`: when you leave it out, Jetlog picks one. Send your own UUID when another operation in the same proposal refers to the record. |
| `data` | An object with the fields to set. For `update`, send only the fields that change. Leave it out for `delete`. |
| `add_self` | Optional, on an `entry` create only. See [Putting the pilot on a new flight](#putting-the-pilot-on-a-new-flight). It sits next to `op`, not inside `data`. |

The rules:

- A proposal has between 1 and 200 operations.
- Two operations on the same record in one proposal are refused.
- A `create` whose `id` already exists is refused, and so is an `update` or `delete` of an `id` that does not exist.
- A text value is at most 2000 characters.
- Jetlog applies people first and flights second, so a flight can refer to a person created in the same proposal.
- A `delete` removes the flight or person. The pilot can undo an approved delete in the Jetlog app.
- Use the import route for flights your app added, and for new flights. A proposal is for changes the pilot needs to approve.
- Fields for files, photos, signatures and signing links are not available to an app. A proposal that sets a signature or a photo, or that uses one of those resources, is refused. Do not send them.

### Fields of a flight

These are the fields of `data` for `resource` `entry`. Send `type` and `date` when you create a flight.

| Field | Meaning |
| :-- | :-- |
| `type` | `flight`. Required on create. |
| `date` | `YYYY-MM-DD`. Required on create. |
| `flight_number` | The flight number. |
| `registration` | The registration. Jetlog strips separators and uses uppercase. |
| `from`, `to` | The planned airports, as ICAO codes. |
| `actual_from`, `actual_to` | The airports actually used, as ICAO codes, when they differ from the plan. |
| `scheduled_off_blocks` | The planned off blocks time, `HH:MM` zulu. |
| `off_blocks`, `airborne`, `touchdown`, `on_blocks` | The actual times, `HH:MM` zulu. |
| `update_flight_data` | `true` lets Jetlog fill the actual times from its flight tracking, `false` keeps the times as entered. When you create a flight with any actual time and leave this out, Jetlog sets it to `false` so your times show. An update leaves it as it is unless you send it. |
| `remarks` | Free text, at most 1000 characters. A proposal can replace existing remarks, which an import never does. The pilot sees the old and the new text before approving. |
| `people` | The crew, a list of `{"person_id": "...", "role": "..."}`. See below. |
| `takeoffs_and_landings` | `{"type": "auto", "takeoffs": 1, "landings": 1}`, or `{"type": "manual", "takeoffs_day": 1, "takeoffs_night": 0, "landings_day": 1, "landings_night": 0}`. Always send `type`. |
| `approaches` | A list such as `[{"type": "ils_cat1", "count": 1}]`. The types are the ones in the [README](README.md#payload-schema-shared). |
| `go_arounds`, `passengers_on_board` | Whole numbers, 0 or more. |
| `fuel_planned`, `fuel_used`, `cargo_on_board` | Whole numbers of kilograms, 0 or more. |
| `is_deleted` | `true` removes the flight, the same as a `delete` operation. |

`people` works per person. A person you list is added to the flight or gets the role you send, and a person you leave out stays as they are. To remove a crew member, send them with `"is_deleted": true`. Each `person_id` is the id of a person in the pilot's crew list (`GET /people`), the id of a person your proposal creates, or `SELF` for the pilot. `role` is free text such as `PIC` or `FO`, and it is required.

### Putting the pilot on a new flight

When an `entry` create does not list the pilot in `people`, Jetlog adds the pilot as crew with their default role. That is the role on the pilot's own person, or else the role on the pilot's most recent flight. When no default role can be found, the proposal is refused with an error on `people`, so send `{"person_id": "SELF", "role": "..."}` yourself. When the pilot was not crew on the flight, set `"add_self": false` on the operation.

### Fields of a crew member

These are the fields of `data` for `resource` `person`.

| Field | Meaning |
| :-- | :-- |
| `first_name`, `last_name` | The name. Send both when you create a person. |
| `default_role` | The role Jetlog suggests for this person. |
| `employee_number` | An employee number. |

Creating a person does not look for an existing one, so read `GET /people` first and use the id of a person who is already there.

### Change a field on an existing flight

Send only the fields that change, and as many of them as you need. This proposal corrects two times and keeps them as entered. The earlier example under [POST /changes](#post-changes) changes the registration. The pilot sees the flight before and after.

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/changes \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Fix the times of KL1023 on 14 August",
    "operations": [
      {
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {
          "off_blocks": "14:10",
          "on_blocks": "15:07",
          "update_flight_data": false
        }
      }
    ]
  }'
```

### Add crew to an existing flight

Anna de Vries is already in the pilot's crew list, so the operation uses her id from `GET /people`. The pilot stays on the flight, because crew you do not mention is left alone.

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/changes \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Add the first officer to KL1023 on 14 August",
    "operations": [
      {
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {
          "people": [
            {"person_id": "4d6e8a21-95f3-4b7c-a1d2-3e5f60718293", "role": "FO"}
          ]
        }
      }
    ]
  }'
```

### Add a crew member who is not in the logbook yet

Two operations in one proposal. The first creates the person with an id you choose, and the second adds that person to the flight. The pilot can only approve the second operation together with the first.

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/changes \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Add Lars Visser as purser on KL1023 on 14 August",
    "operations": [
      {
        "op": "create",
        "resource": "person",
        "id": "9a2c4e6f-1b3d-4f57-8a9b-0c1d2e3f4a5b",
        "data": {"first_name": "Lars", "last_name": "Visser", "default_role": "Purser"}
      },
      {
        "op": "update",
        "resource": "entry",
        "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01",
        "data": {
          "people": [
            {"person_id": "9a2c4e6f-1b3d-4f57-8a9b-0c1d2e3f4a5b", "role": "Purser"}
          ]
        }
      }
    ]
  }'
```

### Delete a flight

A delete needs the id and nothing else. The pilot sees the flight and that it would be removed.

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/changes \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Remove KL1023 on 14 August, it was never flown",
    "operations": [
      {"op": "delete", "resource": "entry", "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01"}
    ]
  }'
```

## Errors per route

Every route can also answer the errors in [Calling the routes](#calling-the-routes).

| Route | Status | Body | Meaning |
| :-- | :-- | :-- | :-- |
| `POST /import` | | | See [Errors on the token route](MIGRATION.md#errors-on-the-token-route). |
| `GET /entries` | `400` | `{"error":"invalid_date"}` | `from`, `to` or `after_date` is not a `YYYY-MM-DD` date. |
| `GET /entries` | `400` | `{"error":"invalid_type"}` | `type` is not `flight` or `fstd`. |
| `GET /entries` | `400` | `{"error":"invalid_parameter"}` | `limit` is not a number, or `include_deleted` is not `true` or `false`. |
| `GET /entries/:id` | `404` | `{"error":"not_found"}` | No such flight for this pilot, or it was removed. |
| `GET /totals` | `400` | `{"error":"invalid_date"}` | `from` or `to` is not a `YYYY-MM-DD` date. |
| `POST /changes` | `403` | `{"error":"insufficient_scope", ...}` | The proposal touches something an app can never use, such as a photo. |
| `POST /changes` | `409` | `{"error":{"message":"Too many open pending changes","code":"open_cap_reached"}}` | The pilot already has 20 open proposals. Wait for the pilot to decide on some, or for them to expire. |
| `POST /changes` | `413` | `{"error":{"message":"Too many operations (201)","code":"too_many_entries"}}` | More than 200 operations. Nothing was stored. |
| `POST /changes` | `422` | `{"error":{"message":"Invalid operations","errors":[...]}}` | One or more operations are not valid. Nothing was stored. |
| `GET /changes/:id` | `404` | `{"error":{"message":"Pending change not found"}}` | No such proposal for this connection. |

`GET /me`, `GET /people` and `GET /aircraft` have no errors of their own.

A `422` lists what is wrong in `errors`. Each item has the `index` of the operation (`null` when it concerns the whole proposal), the `field`, and a `message`:

```json
{
  "error": {
    "message": "Invalid operations",
    "errors": [
      {"index": 0, "field": "id", "message": "entry c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01 not found"},
      {"index": 1, "field": "people", "message": "unknown person_id(s): 4d6e8a21-95f3-4b7c-a1d2-3e5f60718293"}
    ]
  }
}
```

## Limits

| What | Limit |
| :-- | :-- |
| Entries in one import request | 200 |
| People in one import request | 1000 |
| Operations in one proposal | 200 |
| Open proposals per pilot, all apps and assistants together | 20 |
| Lifetime of a proposal | 24 hours |
| Length of a summary | 500 characters |
| Length of a text value in an operation | 2000 characters |
| Flights per page of `GET /entries` | 50 by default, 200 at most |
| Access token | 1 hour |
| Refresh token | 90 days, replaced on every use |

Requests are also limited per pilot over time. When you go over, the route answers `429` with a `Retry-After` header. Wait that many seconds, then send the same request.

## What an app can never do

At either level, an app cannot:

- apply its own proposal. Approving is an action of the pilot in the Jetlog app, and no partner route applies a proposal.
- read, add or download files, photos and signature images, or create signing links.
- call anything outside the routes in this document. A partner token is refused everywhere else.
- act without the pilot. Every connection is made by a pilot approving it, and the pilot can remove it at any time.
- read proposals that another connection made.

At the own flights level an app also cannot read the logbook or propose changes. At the whole logbook level it still cannot change a flight it did not add without the pilot approving that change.

## The sample app

The [Jetlog sample app](https://github.com/jvdvleuten/jetlog-sample-app) is a small web app that runs the whole flow against a pilot's own account. It sends the authorization request, receives the callback, exchanges the code, reads the logbook and proposes a change, and then follows the proposal until the pilot has decided. It is registered as a partner itself, so you can run it with your own account before your own app is registered, and read its code as a starting point.
