# Partner API reference

This is the reference for everything an app can call once a pilot has connected it to their Jetlog logbook. The [README](README.md) describes the payload of the import route. [MIGRATION.md](MIGRATION.md) covers registering your app and the connection itself: the developer console, the registration form, the metadata document, the authorization request, the token exchange and refreshing. This page covers what a connected app can do with its token, route by route.

Words used on this page:

- A **partner** is an app or service that works on behalf of pilots.
- A **pilot** is the person whose logbook it is.
- The **token route** is the import route, `POST /api/partner/v1/import`.
- The **read routes** and the **proposal routes** are the other routes listed under [The routes](#the-routes).

To see a connection work before you build anything, run the [sample app](#the-sample-app).

Sections:

1. [Access levels](#access-levels)
2. [Asking for a level](#asking-for-a-level)
3. [Connecting an app, step by step](#connecting-an-app-step-by-step)
4. [The routes](#the-routes)
5. [Calling the routes](#calling-the-routes)
6. [Reading the logbook](#reading-the-logbook)
7. [Proposing changes](#proposing-changes)
8. [The operations format](#the-operations-format)
9. [Errors per route](#errors-per-route)
10. [Limits](#limits)
11. [What an app can never do](#what-an-app-can-never-do)
12. [The sample app](#the-sample-app)

## Access levels

A pilot connects a partner at one of two levels. The pilot chooses when approving the connection in the Jetlog app.

| Level | Scope in the token | What the app can do |
| :-- | :-- | :-- |
| Own flights | `import` | Add flights with their crew, and change or remove the flights it added, through the import route. Nothing else. |
| Whole logbook | `import read write` | Everything the own flights level can do. It can also read the whole logbook, and propose changes to flights and crew members. A proposal changes nothing until the pilot approves it in the Jetlog app. |

The three scopes mean this:

- `import` is the direct import of the app's own flights through the token route.
- `read` is reading the logbook through the read routes.
- `write` is proposing changes. It never applies them.

Flights an app adds through the import route are written directly at both levels, and the app changes or removes those through the import route as well. At the whole logbook level, a change to a flight or crew member the app did not add can only be proposed. Whatever an app sends, it cannot change a flight it did not add unless the pilot approves that change.

The pilot can always grant the lower level when the wider one was asked. The pilot can also remove the app at any time under Settings > Connected Apps, which ends the connection.

## Asking for a level

The level is requested with the `scope` parameter of the authorization request, which [MIGRATION.md](MIGRATION.md#3-build-the-authorization-request) describes in full.

- `scope=import` asks for own flights. The pilot is not offered a choice, and the token carries exactly `import`.
- `scope=import read write` asks for the whole logbook and lets the pilot choose between the two levels.
- A request that does not contain both `read` and `write` is handled as `import`.

The whole logbook level is available only to an app that has all of these:

- Jetlog has switched the access on for the app. Once your app is approved, you ask for it on the app's page in the developer console (`https://jetlog.app/developers/console`) with a short reason, and Jetlog decides per app and emails the decision.
- The app has a client secret. You generate it on the same page, and Jetlog shows it once. An app that has a client secret sends it as `client_secret` in the body of every request to the token endpoint, for the code exchange and for every refresh.
- The app has approved redirect addresses. Jetlog approves the addresses of your app, the ones on its page in the console or in its document, when it approves your app.
- None of the approved redirect addresses is a loopback address (`localhost`, `127.0.0.1` or `[::1]`). An app that runs on the pilot's own computer therefore works at the own flights level.

[MIGRATION.md](MIGRATION.md#1-register-your-app) describes the registration, and [step 2](MIGRATION.md#2-review-development-and-the-client-secret) the client secret. While your app is waiting for review, your own Jetlog account can use the whole logbook level without Jetlog's switch and without approved addresses, as long as the app has a client secret and no loopback address. That lets you build and test the read routes and the proposals before the review is done. For an app that does not meet all of these, a request for `import read write` is narrowed to `import` without any error. The pilot is offered the own flights level only, and the token response says `"scope": "import"`.

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

When the pilot picks own flights, or the app does not meet the conditions for the whole logbook, the same response says `"scope": "import"`. Read `scope` from the token response and not from your own request. When `read` or `write` is missing, do not call the read routes or the proposal routes. They answer `403` with `insufficient_scope`.

A refresh keeps the level that was granted. To get another level, send the pilot through the authorization request again.

A request for the whole logbook looks like this. It is the request from MIGRATION.md with a different `scope`. `client_id` is the app id from the developer console, or the address of your metadata document, which is what the example shows:

```sh
AUTH_URL="https://jetlog.app/oauth/authorize?response_type=code&client_id=https%3A%2F%2Fpartner.example.com%2Fjetlog-client.json&redirect_uri=https%3A%2F%2Fpartner.example.com%2Foauth%2Fjetlog%2Fcallback&scope=import%20read%20write&state=${STATE}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&resource=https%3A%2F%2Fjetlog.app%2Fapi%2Fpartner%2Fv1"
open "$AUTH_URL"    # macOS. On Linux use xdg-open.
```

What the pilot sees when you ask for the whole logbook:

- The Jetlog app shows your name and a choice between "Only its own flights" and "My whole logbook", each with a sentence on what it means. The wider choice is never preselected.
- The page used when a pilot signs in with an email code instead of the app offers the same two choices as radio buttons, with neither selected.
- Approving at this level needs a current version of the Jetlog app.
- Afterwards, Settings > Connected Apps shows the level the pilot chose.
- Each time an app is connected, Jetlog emails the pilot about it, with the name of the app and the level.

When you ask for `import`, the pilot sees the screen described in [MIGRATION.md](MIGRATION.md#what-the-pilot-sees-on-the-same-phone), and nothing changes for you.

If Jetlog later switches the whole logbook level off for an app, or the app stops meeting one of the conditions above, the tokens that hold it lose the read routes and the proposal routes at once, including the status of proposals already made. Those routes answer `403` with `insufficient_access`. The switch is checked on every request, so a refresh still works and the token keeps saying `import read write`. The import route keeps working. A proposal that was already waiting stays open, and the pilot can reject it but not approve it. It can be approved again when the level is switched back on.

## Connecting an app, step by step

This is a whole connection in order. The examples use the address of the example metadata document in [MIGRATION.md](MIGRATION.md#with-a-metadata-document) as `client_id`. An app registered with the form puts its app id there, for example `jetlog_app_VUGENuUg7Q6UL-CGr67N8aEz5Q_ZvwfKxWeBYz0Bd9s`, and every other value stays the same. `STATE`, `CODE_VERIFIER` and `CODE_CHALLENGE` are made as [MIGRATION.md](MIGRATION.md#3-build-the-authorization-request) describes. `CLIENT_SECRET` is the client secret of an app that has one.

### 1. Send the pilot to Jetlog

```sh
open "https://jetlog.app/oauth/authorize?response_type=code&client_id=https%3A%2F%2Fpartner.example.com%2Fjetlog-client.json&redirect_uri=https%3A%2F%2Fpartner.example.com%2Foauth%2Fjetlog%2Fcallback&scope=import%20read%20write&state=${STATE}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&resource=https%3A%2F%2Fjetlog.app%2Fapi%2Fpartner%2Fv1"
```

When the pilot has approved in the Jetlog app, the browser comes back to your redirect address with `code` and `state`. When the pilot declined or cancelled, it comes back with `error=access_denied`. A problem with the request itself shows the pilot an error page at Jetlog with the error code and a `400`, and the browser is not sent back:

- `invalid_client`: the `client_id` is not known, the redirect address is not one of your app's addresses or not approved, or the document cannot be used. Fix the `client_id`, the address or the document.
- `unauthorized_client`: the app was not approved, was withdrawn or is disabled. Check its page in the developer console. An app that is still waiting for review does not give this answer. The sign-in pages say that it is in development, and only its developer's own account can connect it.
- `invalid_request`, `unsupported_response_type` or `invalid_target`: a parameter is wrong, for example the PKCE challenge or the `resource`.

### 2. Exchange the code

```sh
# An app without a client secret leaves out the last line.
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=authorization_code \
  --data-urlencode "code=$CODE" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json" \
  --data-urlencode "redirect_uri=https://partner.example.com/oauth/jetlog/callback" \
  --data-urlencode "code_verifier=$CODE_VERIFIER" \
  --data-urlencode "resource=https://jetlog.app/api/partner/v1" \
  --data-urlencode "client_secret=$CLIENT_SECRET"
```

```json
{
  "access_token": "jlp_example_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "jlr_example_refresh_token",
  "scope": "import read write"
}
```

When the exchange succeeds, Jetlog emails the pilot that the app was connected.

- `401` `{"error":"invalid_client"}`: the app has a client secret and the request has none or a wrong one. The code is not used up, so repeat the request with the right secret.
- `400` `{"error":"invalid_grant"}`: the code is older than 60 seconds, was used before, or one of `client_id`, `redirect_uri`, `code_verifier` and `resource` differs from the authorization request. Start again at step 1.

### 3. Call the API

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/import \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL"}],"people":[]}'
```

The answer is `{"data": "OK", "skipped": []}`. Read `skipped` and `warnings` on every answer.

- `401` `{"error":"invalid_token"}`: the access token expired. Refresh it (step 4) and send the request again once.
- `403` `{"error":"insufficient_scope"}` on a read or proposal route: the token holds only own flights, because the pilot chose that or the app did not meet the conditions for the whole logbook when the pilot approved. Read `scope` from the token response. `insufficient_access` means the app stopped meeting them later.
- `413` `{"error":"payload_too_large","max_bytes":2097152}`: split the import into smaller requests.

### 4. Refresh the access token

```sh
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=refresh_token \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json" \
  --data-urlencode "client_secret=$CLIENT_SECRET"
```

The answer has the shape of step 2. An app that sent its client secret gets the same `refresh_token` back, and the access tokens from earlier refreshes stay valid until they expire, so refreshes can run in parallel. An app without a client secret gets a new refresh token that replaces the old one, and the old access token stops working. Save the refresh token from the answer before anything else.

- `401` `{"error":"invalid_client"}`: the client secret is missing or wrong. The refresh token is not used up, so repeat the request with the right secret.
- `400` `{"error":"invalid_grant"}`: the refresh token was replaced, expired or revoked, or the pilot removed the app. The pilot connects again.
- `400` `{"error":"unauthorized_client"}`: Jetlog has disabled the app. Keep the refresh token. It works again when the app is enabled.

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

Send `Authorization: Bearer <access_token>` with the access token of the pilot you act for. Requests and responses are JSON, so send `Content-Type: application/json` with a body. The body limits of `POST /changes` and `POST /import` (see [Limits](#limits)) count the bytes Jetlog receives, however the body is sent, also without a `Content-Length` header. Send these two routes a JSON body: a multipart body is not read. Ids are UUIDs, dates are `YYYY-MM-DD` and times are `HH:MM` zulu.

A partner token works on these routes only. The rest of the Jetlog API, and the endpoint of the AI assistants, refuse it with `401`, whatever scopes the token holds.

### Who may call a route

Every route checks the same four things, in this order, and the first one that fails is the answer. The checks of the later steps are not made when an earlier one fails.

| Step | Check | Answer when it fails |
| :-- | :-- | :-- |
| 1 | The token is a live partner token for this API. | `401` `{"error":"invalid_token"}` with `WWW-Authenticate: Bearer error="invalid_token"`. The token is missing, unknown, expired, revoked, or meant for another resource. Refresh it once. If that fails, the pilot connects again. |
| 2 | The token carries the scope the route needs. | `403` `{"error":"insufficient_scope"}`. An own flights token on a read route or a proposal route ends here. |
| 3 | Jetlog has not switched your partner registration off. | `403` `{"error":"integration_disabled"}`. |
| 4 | The read routes and the proposal routes only: Jetlog still has the whole logbook level enabled for your app. | `403` `{"error":"insufficient_access"}`. The import route does not make this check and keeps working. |

So four different answers mean four different things: `401` is about the token, `insufficient_scope` is about what the pilot granted, `integration_disabled` is about your registration, and `insufficient_access` is about the whole logbook level of your app.

### Rate limits

A route can also answer `429` with a `Retry-After` header, in seconds, and the body `{"error":"rate_limited","retry_after":30}`. Wait that long, then send the same request.

Most limits are per connection. A connection is one pilot's approval of your app, and it stays the same when the access token is refreshed. One connection cannot use up the allowance of another connection, of another app, or of the pilot's own tools. The import route is the exception: its limit is per pilot.

| Routes | What is counted | Per |
| :-- | :-- | :-- |
| `GET /me`, `GET /entries`, `GET /entries/:id`, `GET /people`, `GET /aircraft`, `GET /totals`, `GET /changes/:id` | Requests. The read routes and the status poll share one limit. | Connection |
| `POST /changes` | The operations in the request. A request over the limit is refused as a whole and stores nothing. This limit is separate from the one above. | Connection |
| `POST /import` | The entries plus the people in the request. | Pilot |

The sections below add the errors that belong to one route. [Errors per route](#errors-per-route) has them all in one table.

## Reading the logbook

The read routes need the `read` scope. They only read. They return the same JSON that the Jetlog app itself gets from Jetlog, with the same field names.

An app never sees anything about files, photos or signatures. The responses have no signature, attachment or photo fields at all, not even to say that one exists.

### GET /me

Who the pilot is, as far as the logbook goes. The body is exactly `user_id` and `self_person_id`, and nothing else: no email address and no account details. `user_id` is the pilot's id. `self_person_id` is the id the pilot has as a crew member, which is the `person_id` of the pilot in the `people` of a flight. To get the pilot's name, find the person with that id in `GET /people`.

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

Lists flights and simulator sessions, oldest first, by the date they took place and then by id. Removed flights are never returned, and neither are crew rows that were removed from a flight. A parameter `include_deleted` is accepted and has no effect.

| Parameter | Meaning |
| :-- | :-- |
| `from`, `to` | First and last date to include, `YYYY-MM-DD`. They compare with the date the flight took place, which is `derived.date` in the response. |
| `type` | `flight` or `fstd`. Without it both come back. `fstd` is a simulator session. |
| `registration` | Registration as Jetlog stores it, uppercase without separators, for example `PHBXD`. |
| `airport` | An airport code, ICAO or IATA. It matches flights that departed from or arrived at that airport. |
| `flight_number` | A flight number. The match ignores case. |
| `person_id` | Only flights with this crew member. Take the id from `GET /people`. |
| `role` | Only together with `person_id`. Only flights where that crew member had this role. |
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
      "is_own": false
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

- `derived` is the flight as the logbook shows it, and it is the part to read. While `update_flight_data` is `true`, Jetlog follows the flight on its own: the actual times and the registration come from Jetlog's flight feed, and so do the date and the airports once the feed knows them. The plain fields (`date`, `registration`, `from`, `to`, `off_blocks` and the other times) then show what was entered before, which can be empty or different. When `update_flight_data` is `false`, `derived` shows the plain fields, except that an actual airport the pilot logged for a diversion wins over the planned one.
- `is_own` is `true` when your app created the flight, through the import route or an approved proposal, and `false` for every other flight. Those flights are the ones the import route can change directly.
- `version` and `updated_at` change whenever the flight changes.
- `people` lists the crew. Each `person_id` is an id from `GET /people`. The pilot's own id is `self_person_id`.
- `calculated_times` is `null` while Jetlog has not calculated the flight yet. Otherwise it holds whole minutes per figure, with the same figure names as `totals` below, plus `cross_country_distance` and `computed_at`.
- Removed flights and removed crew rows are left out. A crew row in `people` always has `is_deleted` set to `false`.

To read the next page, send the cursor back:

```sh
curl -sS "https://jetlog.app/api/partner/v1/entries?from=2026-08-01&to=2026-08-31&airport=EHAM&limit=1&after_date=2026-08-14&after_id=c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Keep the other parameters the same. The last page has `"has_more": false` and `"next_cursor": null`.

Errors: `400` with `{"error":"invalid_date"}` for a `from`, `to` or `after_date` that is not a date, `{"error":"invalid_type"}` for a `type` that is not `flight` or `fstd`, and `{"error":"invalid_parameter"}` for a `limit` that is not a number.

### GET /entries/:id

One flight. The answer is `{"entry": {...}}`. The flight has the same fields as a row of the list above. An id that does not exist, belongs to another pilot or was removed answers `404` with `{"error":"not_found"}`.

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
    "is_own": true
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
      "is_imported_from_other_logbook": false
    },
    {
      "id": "4d6e8a21-95f3-4b7c-a1d2-3e5f60718293",
      "first_name": "Anna",
      "last_name": "de Vries",
      "default_role": "FO",
      "employee_number": null,
      "is_imported_from_other_logbook": false
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
2. Jetlog sends the pilot a notification titled "Changes to review", with a text such as "Example Partner wants to change 3 flights." Jetlog writes that text itself, from the name Jetlog registered for your app and the number of operations. Nothing you send is part of it, the summary included. The proposal also waits in the pilot's list of changes to review in the Jetlog app, and tapping the notification opens it.
3. The pilot opens the proposal in the Jetlog app and sees what every operation would change, before and after. The pilot approves all of it, approves only some of the operations, or rejects it. Reviewing a proposal needs a current version of the Jetlog app.
4. The app asks `GET /changes/:id` for the status until the status is no longer `pending`. The pilot decides at their own speed, so once a minute is plenty. Every poll counts against the same limit as your reads, see [Rate limits](#rate-limits).
5. When the pilot approved, the changes are in the logbook. The pilot can still undo an approved change in the Jetlog app.

A proposal that nobody decides expires 24 hours after it was made. A connection can have 5 open proposals at a time. The limit is per connection, so your app does not use up the allowance of the pilot's AI assistants or of another app, and they do not use up yours. A proposal holds up to 200 operations.

Every `POST /changes` makes a new proposal. After a timeout, do not send the same request again without thinking: the pilot would be asked about the same change twice. There is no route to list proposals, so keep the `id` from the answer.

A proposal belongs to the connection that made it, and it stays reachable across token refreshes. After a pilot disconnects your app and connects it again, the new connection cannot read the proposals of the old one. A proposal sent on a connection the pilot has just disconnected is not stored, and the answer is `401` with `invalid_token`.

Approving also needs the connection to be live. The pilot can approve a proposal only while your app is still connected and Jetlog still has the whole logbook level enabled for it.

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
| `operations` | Your operations as Jetlog stored them. Each one has an `index` that counts from 0, and every create has an `id`. Once the proposal is `applied`, each operation also has `applied`, which is `true` when its change was made and `false` when it was not. See [Partial approval](#partial-approval). |
| `preview` | One item per operation. This is what the pilot reviews. Each item has exactly `index`, `op`, `resource` and `id` (the same as the operation), `before` and `after` (the flight or person as it is and as it would be) and `changed_fields` (the names of the fields that change). A create has `null` for `before`, and a delete shows `is_deleted` going to `true` in `after`. |
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
        "data": {"registration": "PHBXE"},
        "applied": true
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
| `stale` | When the pilot approved, a flight or person the proposal touches had changed since it was proposed. Nothing was changed. The proposal stays open with a refreshed preview, so the pilot can still approve or reject it, and it still counts as open until it is decided or expires. You can also send a new proposal built from current data. |
| `failed` | Applying it did not work, for example because a flight it touches was removed in the meantime. Nothing was changed. `error` holds a short reason. |
| `revoked` | The connection that made the proposal ended before the pilot decided. Nothing was changed. See below. |

Poll until the status is no longer `pending`. Every other status is final, except `stale`, which stays open until the pilot decides or the 24 hours pass.

When a connection ends, because the pilot removes the app under Settings > Connected Apps or your app revokes its refresh token or its current access token, Jetlog marks all open proposals of that connection `revoked`. The token stops working at the same moment, so your app cannot read this status. The status exists for the pilot's side. An app that disconnects a pilot should treat that pilot's open proposals as gone. A new connection of the same pilot cannot read the proposals of the old one either: they answer `404`.

### Partial approval

The pilot may approve only some of the operations of a proposal. The status is then `applied`, and `counts` describes only what was applied. Each operation says whether it landed in its `applied` field:

```json
{
  "operations": [
    {"index": 0, "op": "create", "resource": "person", "id": "9a2c4e6f-1b3d-4f57-8a9b-0c1d2e3f4a5b", "data": {"first_name": "Lars", "last_name": "Visser"}, "applied": true},
    {"index": 1, "op": "update", "resource": "entry", "id": "c1f0a5e4-8b2d-4d7a-9f31-5a6e7b8c9d01", "data": {"remarks": "Late departure"}, "applied": false}
  ]
}
```

`applied` is `true` when the change was made. It is `false` when the pilot left the operation out, and also when the operation changed nothing. The operations that were left out are not offered again. To propose them again, send a new proposal. The field appears only once the proposal is `applied`.

Operations that depend on each other can only be approved together. A flight that lists a crew member created in the same proposal needs the operation that creates that person.

### After approval

The pilot can undo an approved change in the Jetlog app. The status then stays `applied`, and `reverted_indices` lists the operations that were undone. Flights an app creates through an approved proposal are its own flights afterwards, with `is_own` set to `true`, so the app can change them through the import route.

## The operations format

An operation describes one change to one record.

| Field | Meaning |
| :-- | :-- |
| `op` | `create`, `update` or `delete`. |
| `resource` | `entry` for a flight, or `person` for a crew member. Other resources are not part of the partner API. |
| `id` | The id of the flight or person. Required for `update` and `delete`. Optional for `create`: when you leave it out, Jetlog picks one. Send your own UUID when another operation in the same proposal refers to the record. |
| `data` | An object with the fields to set. For `update`, send only the fields that change. A `delete` takes no `data`: leave it out. A key in the `data` of a `delete` is refused with a `422` that names the key. |
| `add_self` | Optional, on an `entry` create only. See [Putting the pilot on a new flight](#putting-the-pilot-on-a-new-flight). It sits next to `op`, not inside `data`. |

The rules:

- A proposal has between 1 and 200 operations.
- Two operations on the same record in one proposal are refused, with the `id` message `duplicate entry id <id> within this proposal` (or `duplicate person id <id> within this proposal`). Put every change to one record in one operation.
- A `create` whose `id` already exists is refused.
- An `update` or `delete` can only target a flight or a crew member that the read routes can show. A flight that was removed, a simulator session, an id that does not exist and a record of another pilot all answer `entry <id> not found` (or `person <id> not found`).
- A text value is at most 2000 characters, and every value in `data` is a single value. Only `people` is a list.
- Jetlog applies people first and flights second, so a flight can refer to a person created in the same proposal.
- A `delete` removes the flight or person. The pilot can undo an approved delete in the Jetlog app.
- A proposal can target any flight of the pilot, including one your app added. The import route changes those flights without approval, so use it for your own flights and new flights, and use a proposal for the rest.
- Flights your app creates through an approved proposal become its own flights, so the import route can change them afterwards. An approved update to an existing flight does not make that flight the app's own.
- The rules about what a proposal may contain are checked when the proposal is made and again when the pilot approves it: the resources, the fields and their sizes, the flight type, no `data` on a `delete`, no other field next to `"is_deleted": true`, and a true or false `is_deleted`. Two checks are made only when the proposal is made: that an `update` or `delete` targets a flight or crew member the read routes can show, and that the logbook would show the value you proposed. At approval Jetlog checks instead that the connection is still live, that your app still has the whole logbook level, and that nothing the proposal touches changed since it was made. A change since then makes the status `stale`, see [Statuses](#statuses).

### What a proposal may contain

The pilot reviews a proposal by looking at a before and an after value for everything it would change. So a proposal can only carry fields that the review shows, and one more rule holds: after the change, the logbook must show exactly the value your proposal set. Jetlog compares the two after the usual cleaning, which means the registration is cleaned, airport codes are in capital letters, times are read, text is trimmed, and crew is compared per person and role. When the logbook would show anything else, the proposal is refused. A proposal that repeats a value that is already there is accepted.

A proposal also cannot change a value that the pilot's own device changed more recently than the moment of the proposal. The pilot's later change wins, so the logbook would not show your value, and the proposal is refused with a `422` that names the field.

Everything that breaks a rule is refused with a `422` that names the field, and nothing is stored. A key that is not in the lists below is refused too, whatever its name, and it is never ignored silently.

Proposing has no effect outside the preview Jetlog keeps for the pilot. The logbook is not changed, and nothing about it is sent to the pilot's devices, until the pilot approves. The only thing the pilot gets before that is the notification about the proposal.

Only two resources can be proposed, `entry` for a flight and `person` for a crew member. A flight is always type `flight`: a create must say `"type": "flight"`, and an update cannot change the type.

### Fields of a flight

These are the fields of `data` for `resource` `entry`. Send `type` and `date` when you create a flight.

| Field | Meaning |
| :-- | :-- |
| `type` | `flight`. Required on create. |
| `date` | `YYYY-MM-DD`. Required on create. |
| `flight_number` | The flight number. |
| `registration` | The registration. Jetlog strips separators and uses uppercase. |
| `from`, `to` | The airports. Send ICAO codes in capital letters. A proposal stores a code exactly as sent. It does not convert IATA codes to ICAO the way the import route does. |
| `off_blocks`, `airborne`, `touchdown`, `on_blocks` | The actual times, `HH:MM` zulu. |
| `remarks` | Free text, at most 1000 characters. A proposal can replace existing remarks, which an import never does. The pilot sees the old and the new text before approving. |
| `people` | The crew, a list of at most 20 objects `{"person_id": "...", "role": "..."}`. See below. |
| `is_deleted` | `true` removes the flight, the same as a `delete` operation. It has to be a JSON boolean, so `"true"` and `1` are refused. To remove a flight, send a `delete` without `data`, or an `update` whose `data` is only `"is_deleted": true`. An operation that sets it to `true` carries no other field, whichever way it is sent, because the pilot reviews a deletion as the flight that goes away and has nothing else to look at. Any other key next to it is refused with a `422` that names the key. Either way the preview shows a delete and `counts` counts a deletion. |

`people` works per person. A person you list is added to the flight or gets the role you send, and a person you leave out stays as they are. To remove a crew member, send them with `"is_deleted": true`. A crew member is an object with only `person_id`, `role` and optionally `is_deleted`. Each `person_id` is the id of a person in the pilot's crew list (`GET /people`), the id of a person your proposal creates, or `SELF` for the pilot. `role` is free text such as `PIC` or `FO`, and it is required.

### Fields of a crew member

These are the fields of `data` for `resource` `person`.

| Field | Meaning |
| :-- | :-- |
| `first_name`, `last_name` | The name. Send both when you create a person. |
| `default_role` | The role Jetlog suggests for this person. |
| `employee_number` | An employee number. |
| `is_imported_from_other_logbook` | `true` when the person came from another logbook. |
| `is_deleted` | `true` removes the person, the same as a `delete` operation. It has to be a JSON boolean, like on a flight, and an `update` that sets it to `true` carries no other field in `data`. |

Creating a person does not look for an existing one, so read `GET /people` first and use the id of a person who is already there.

### Flights that Jetlog tracks

While `update_flight_data` is `true` on a flight, Jetlog follows it on its own. The actual times and the registration come from Jetlog's flight feed, and so do the date and the airports once the feed has them. The logbook then shows the feed's value, not yours, so a proposal for such a value is refused, unless it is the value the logbook already shows:

- On a tracked flight, `off_blocks`, `airborne`, `touchdown`, `on_blocks` and `registration` are decided by the feed. This holds even when the feed has not filled in a registration yet.
- `date`, `from` and `to` are decided by the feed once it knows them. You can tell by comparing `derived` with the plain fields in the read routes: when `derived.from` is not `from`, the feed decides the route.
- `flight_number`, `remarks`, `people` and a removal are shown as proposed whatever the feed does, so they can always be proposed.
- On a flight that is not tracked, all the fields above can be proposed. A mismatch can still happen there. For example the actual airport the pilot logged for a diversion wins over `from` and `to`, so a proposal for those is refused too.
- A new flight that carries at least one actual time is not tracked, so its times show and can be proposed together with its registration. A new flight without any actual time is tracked, so a `registration` on it is refused. Send the registration through the import route instead.

The message says why. When the flight follows the feed and the key is one the feed decides (`date`, `from`, `to`, `registration`, `off_blocks`, `airborne`, `touchdown`, `on_blocks`), it names the feed. Every other mismatch gets the same message without the feed.

### What cannot be proposed

Anything that is not in the two tables above cannot be proposed. That includes the logged hours, takeoffs and landings, approaches, fuel, passengers, cargo, go-arounds, the completed flag, the tracking switch `update_flight_data`, the planned off blocks time, the actual airports of a diversion, aircraft and simulator sessions. An app sets the values of its own flights through the import route, which takes all of these. A flight of the pilot that the app did not add cannot get them from an app at all.

### Refused with 422

The answer is the nested `422` body of [Errors per route](#errors-per-route), with one item in `errors` for each problem, naming the `field` and the `index` of the operation. The messages:

| `field` | `message` |
| :-- | :-- |
| The key itself, for example `manual_times` | `connected apps cannot propose manual_times` |
| The key itself, for example `off_blocks`, when the flight follows the flight feed | `Jetlog would show a different value than the one proposed for this flight, because the flight follows the flight feed, so connected apps cannot propose it` |
| The key itself, for any other mismatch | `Jetlog would show a different value than the one proposed for this flight, so connected apps cannot propose it`. For a person the word `flight` is `person`. |
| `type` | `connected apps can only add flights (type "flight")`, or `connected apps can only change flights (type "flight")` on an update |
| `resource` | `connected apps cannot propose changes to aircraft`, and the same for `fstd` |
| `id` | `entry <id> not found`, or `person <id> not found`, and `duplicate entry id <id> within this proposal` when two operations name one record |
| `people` | `at most 20 crew members per flight`, `each crew member is an object with person_id and role`, or `must be a list of crew members` |
| The key itself, for example `remarks` | `must be a single value` |
| `is_deleted` | `must be true or false` |
| The key itself, for example `flight_number`, in the `data` of a `delete` | `a delete carries no data, flight_number is not allowed` |
| The key itself, for example `flight_number`, next to `"is_deleted": true` in the `data` of an `update` | `a deletion carries no other data, flight_number is not allowed` |

### What a proposal cannot contain

An app never holds the permissions for files or signatures, so a proposal that touches them is refused when it is made, and again if it is somehow approved. Sending the stored value back, or `null`, does not make an exception. These are refused:

| Where | What | Missing permission |
| :-- | :-- | :-- |
| `resource` | `entry_attachment` | `files` |
| `resource` | `signature_link` | `signatures` |
| `data` of an `entry` | `signature`, `signature_attachment_id`, `signature_sha256`, `signature_waived` | `signatures` |
| `data` of a `person` | `photo_attachment_id`, `photo_sha256` | `files` |

The answer is always `403` with a flat body that names the missing permission, and nothing is stored:

```json
{
  "error": "insufficient_scope",
  "message": "Connected apps never get the \"files\" permission. Nothing was changed.",
  "missing_scopes": ["files"]
}
```

For the signature keys and for `signature_link` the message and `missing_scopes` say `"signatures"` instead. A proposal that hits both lists both. Leave these keys and resources out of your proposals.

### Putting the pilot on a new flight

When an `entry` create does not list the pilot in `people`, Jetlog adds the pilot as crew with their default role. That is the role on the pilot's own person, or else the role on the pilot's most recent flight. When no default role can be found, the proposal is refused with an error on `people`, so send `{"person_id": "SELF", "role": "..."}` yourself. When the pilot was not crew on the flight, set `"add_self": false` on the operation.

### Change a field on an existing flight

Send only the fields that change, and as many of them as you need. This proposal corrects two times on a flight that Jetlog does not track, which is why the times can be proposed (`update_flight_data` is `false` for it in the read example above). The earlier example under [POST /changes](#post-changes) changes the registration of the same flight. The pilot sees the flight before and after.

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
          "on_blocks": "15:07"
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

Every route can also answer the access errors in [Who may call a route](#who-may-call-a-route) and `429` as described under [Rate limits](#rate-limits).

The shape of an error depends on the route. The access errors, the import route and the read routes answer with a flat body, `{"error":"<code>"}`. The proposal routes answer with a nested body, `{"error":{"message":"...","code":"..."}}`, except for three flat answers: the `401` for a connection that was just disconnected, the refusal of files and signatures (which has a `message` and `missing_scopes` next to `error`), and the `413` for a body that is too large.

| Route | Status | Body | Meaning |
| :-- | :-- | :-- | :-- |
| `POST /import` | | | See [Errors on the token route](MIGRATION.md#errors-on-the-token-route). |
| `POST /import` | `413` | `{"error":"payload_too_large","max_bytes":2097152}` | The body is larger than 2 MB. The limit holds however the body is sent and is applied before anything else, so even before the token. |
| `GET /entries` | `400` | `{"error":"invalid_date"}` | `from`, `to` or `after_date` is not a `YYYY-MM-DD` date. |
| `GET /entries` | `400` | `{"error":"invalid_type"}` | `type` is not `flight` or `fstd`. |
| `GET /entries` | `400` | `{"error":"invalid_parameter"}` | `limit` is not a number. |
| `GET /entries/:id` | `404` | `{"error":"not_found"}` | No such flight for this pilot, or it was removed. |
| `GET /totals` | `400` | `{"error":"invalid_date"}` | `from` or `to` is not a `YYYY-MM-DD` date. |
| `POST /changes` | `401` | `{"error":"invalid_token"}` | The pilot disconnected your app a moment ago, after the token was accepted. Nothing was stored. The pilot has to connect again. |
| `POST /changes` | `403` | `{"error":"insufficient_scope","message":"...","missing_scopes":["files"]}` | The proposal touches files, photos, signatures or signing links. See [What a proposal cannot contain](#what-a-proposal-cannot-contain). Nothing was stored. |
| `POST /changes` | `409` | `{"error":{"message":"Too many open pending changes","code":"open_cap_reached"}}` | This connection already has 5 open proposals. Wait for the pilot to decide on some, or for them to expire. |
| `POST /changes` | `413` | `{"error":{"message":"Too many operations (201)","code":"too_many_entries"}}` | More than 200 operations. Nothing was stored. |
| `POST /changes` | `413` | `{"error":"payload_too_large","max_bytes":262144}` | The body is larger than 256 KB. The limit holds however the body is sent and is applied before anything else, so even before the token. Nothing was stored. |
| `POST /changes` | `422` | `{"error":{"message":"Invalid operations","errors":[...]}}` | One or more operations are not valid, are not allowed in a proposal (see [Refused with 422](#refused-with-422)), or the summary is missing. Nothing was stored. |
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

A proposal that uses a field outside the lists, or a value that the logbook would not show as proposed, is refused like this. Every problem gets its own item, so one request can show several:

```json
{
  "error": {
    "message": "Invalid operations",
    "errors": [
      {"index": 0, "field": "manual_times", "message": "connected apps cannot propose manual_times"},
      {"index": 0, "field": "off_blocks", "message": "Jetlog would show a different value than the one proposed for this flight, because the flight follows the flight feed, so connected apps cannot propose it"}
    ]
  }
}
```

A body that is too large for the route answers `413` with a flat body that names the limit in bytes:

```json
{"error": "payload_too_large", "max_bytes": 262144}
```

## Limits

| What | Limit |
| :-- | :-- |
| Entries in one import request | 200 |
| People in one import request | 1000 |
| Operations in one proposal | 200 |
| Open proposals per connection | 5 |
| Crew members per flight in a proposal | 20 |
| Body of `POST /changes` | 256 KB |
| Body of `POST /import` | 2 MB |
| Lifetime of a proposal | 24 hours |
| Length of a summary | 500 characters |
| Length of a text value in an operation | 2000 characters |
| Flights per page of `GET /entries` | 50 by default, 200 at most |
| Access token | 1 hour |
| Refresh token | 90 days. An app with a client secret keeps the same refresh token, an app without one gets a new one on every use |

The two body limits count the bytes Jetlog receives, so they hold for a body sent in chunks without a `Content-Length` header too. Send both routes a JSON body: a multipart body is not read.

The open proposals of the pilot's AI assistants are counted separately from yours. Requests are also limited over time, as described under [Rate limits](#rate-limits). When you go over, the route answers `429` with a `Retry-After` header. Wait that many seconds, then send the same request.

## What an app can never do

At either level, an app cannot:

- apply its own proposal. Approving is an action of the pilot in the Jetlog app, and no partner route applies a proposal.
- read, add or download files, photos and signature images, see whether a flight is signed or a person has a photo, or create signing links.
- call anything outside the routes in this document. A partner token is refused everywhere else.
- act without the pilot. Every connection is made by a pilot approving it, and the pilot can remove it at any time.
- read proposals that another connection made.
- propose a change to anything but flights and crew members, or one that the logbook would not show as proposed.

At the own flights level an app also cannot read the logbook or propose changes. At the whole logbook level it still cannot change a flight it did not add without the pilot approving that change.

## The sample app

The [Jetlog sample app](https://github.com/jvdvleuten/jetlog-sample-app) is a small web app that runs the connection flow against a pilot's own account. It sends the authorization request, receives the callback, exchanges the code, adds a flight and keeps its tokens fresh. Jetlog registered it itself, so you can run it as it is with your own account before your own app is registered, and read its code as a starting point. It runs on your own computer, with a redirect address on `127.0.0.1`, so it connects at the own flights level, whatever it asks for. The read routes and the proposals need the whole logbook level, which an app with a loopback redirect address cannot have. Its document needs no `jetlog_developer` field because Jetlog registered it. A document of your own does, see [MIGRATION.md](MIGRATION.md#with-a-metadata-document). An app registered with the form needs no document at all, see [MIGRATION.md](MIGRATION.md#1-register-your-app). The sample needs the Jetlog app on an iPhone or iPad with a logbook, to approve the connection in.
