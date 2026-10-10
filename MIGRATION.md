# Moving to token authentication

This guide is for partners that send flights to Jetlog with the key pair, `Authorization: Bearer <user_key>:<partner_key>` on `/external/v1/import`, and move to the token route. The steps of the token route itself, from registering an app to refreshing a token, are in [GETTING_STARTED.md](GETTING_STARTED.md). This guide covers what is specific to the move: what changes for a partner and for its pilots, how a partner that already uses the key pair links its existing registration, how to run both routes side by side, and what the key route answers. It uses the own flights level, which gives the access the key pair gives. The wider level, with reading and proposals, is described in [PARTNER_API.md](PARTNER_API.md).

Words used in this guide:

- A **partner** is an app or service that sends flights to Jetlog on behalf of pilots.
- A **pilot** is the person whose logbook receives those flights.
- The **key route** is `POST https://jetlog.app/external/v1/import`, authenticated with the key pair.
- The **token route** is `POST https://jetlog.app/api/partner/v1/import`, authenticated with an access token the pilot approved.

Sections:

1. [What changes and what stays the same](#what-changes-and-what-stays-the-same)
2. [Key route and token route compared](#key-route-and-token-route-compared)
3. [Linking your existing registration](#linking-your-existing-registration)
4. [Running both routes side by side](#running-both-routes-side-by-side)
5. [What the key route answers](#what-the-key-route-answers)
6. [Migration checklist](#migration-checklist)

## What changes and what stays the same

**Stays the same**

- The payload. `entries` and `people` follow the schema in the [README](README.md), with the same field rules, the same `null` handling and the same allowlists.
- Matching. An entry is matched per pilot on `date + flight_number + from + to`, exactly as on the key route.
- The response. A successful call returns `{"data": "OK", "skipped": [...]}`, plus `warnings` when there is something to report. The skip reasons are unchanged.
- On the import route a partner only ever changes entries it created. Entries written by the pilot, by a roster import or by another partner are never modified. A row that adds or changes one of them comes back as `duplicate`, and a row with `"is_deleted": true` for one comes back as `unknown`.
- Entries you created with the key pair stay yours after you switch. Both routes attribute flights to the same partner registration, so a token can amend or delete a flight you sent earlier with a key.

**Changes**

- The credential. You send a per-pilot access token instead of the two keys.
- The URL. `/api/partner/v1/import` instead of `/external/v1/import`.
- How a pilot connects. The pilot approves your app in the Jetlog app, instead of copying a key out of it.
- Lifetime. Access tokens last one hour and refresh tokens 90 days. The keys do not expire.
- Signing out everywhere. When the pilot uses "Sign Out Everywhere" in the Jetlog app, the pilot's user key is replaced. The old key answers `401` with `invalid_user_key`, and the pilot has to copy the new key into your app. A token connection ends as well, but the pilot connects again by approving your app in the Jetlog app, with nothing to copy.
- At most 200 entries, 1000 people and 2 MB of body per request on the token route.
- The pilot does not need the external source selected in Jetlog. The connection is listed under Settings > Connected Apps and works next to a calendar or roster source the pilot has set up.
- With `scope=import`, what a token may do is what the key pair may do: add flights with their crew, and change or delete the flights your partner registration created. It cannot read the logbook or touch anything else. A wider level exists and is optional, see [Access levels](GETTING_STARTED.md#access-levels).
- Calls on the token route do not create an import batch in the pilot's list of imports. They are recorded in the audit log.

## Key route and token route compared

| | Key route | Token route |
| :-- | :-- | :-- |
| Endpoint | `POST /external/v1/import` | `POST /api/partner/v1/import` |
| Header | `Authorization: Bearer <user_key>:<partner_key>` | `Authorization: Bearer <access_token>` |
| How a pilot connects | The pilot enables the external source in Jetlog and hands the user key to the partner | The partner starts an authorization request and the pilot approves it in the Jetlog app |
| What the partner stores | One partner key for all pilots, one user key per pilot | One refresh token per pilot. An app with a client secret keeps it on its server, and an app without one uses none |
| Lifetime | Neither key expires | Access token 1 hour. Refresh token 90 days. An app with a client secret keeps the same refresh token, an app without one gets a new one on every use |
| When the pilot signs out everywhere | The user key is replaced and the pilot copies the new key into your app | The connection ends and the pilot approves your app again in the Jetlog app |
| What it may do | Add flights, change and delete the flights the partner created | The same with `scope=import`. A wider level is optional, see [Access levels](GETTING_STARTED.md#access-levels) |
| Requests | No cap documented | At most 200 entries, 1000 people and 2 MB |
| Pilot's source setting in Jetlog | Must be the external source | No requirement |
| How to disconnect | The pilot changes the source in the Source screen of the Jetlog app | The partner calls the revoke endpoint, or the pilot removes the app under Settings > Connected Apps |

## Linking your existing registration

**A partner that already uses the key pair does not register in the console.** Write to support@jetlog.app with the address of your metadata document, and Jetlog links that address to your existing partner registration. This is why flights you created with the keys stay yours. Jetlog tells you when it is done. For a linked document the `jetlog_developer` field is not needed.

Your `client_id` is the address of that document, and the document follows the rules in [With a metadata document](GETTING_STARTED.md#with-a-metadata-document). Until Jetlog has linked the address, an authorization request for it shows the pilot a Jetlog error page with `unauthorized_client` and the status `400`, and the browser is not sent back to your app.

From the authorization request on, the steps are the ones every app follows, starting at [step 4](GETTING_STARTED.md#4-build-the-authorization-request) of the getting started guide.

## Running both routes side by side

Both routes work. The payload is the same, so you can move pilots one at a time.

The key route keeps working unchanged, and its responses carry these headers:

```
Deprecation: true
Link: <https://github.com/jvdvleuten/JetlogAPI/blob/main/MIGRATION.md>; rel="deprecation"
```

No cut-off date is set. When Jetlog sets one, it will be announced to partners before it applies. From then on responses from the key route also carry a `Sunset` header with the date, and after that moment the key route answers `410` with `{"error":"legacy_auth_removed"}`.

Jetlog records use of the key route per partner and per pilot, so it can see who is still on the keys before it switches the route off.

What to do with pilots who are still on a key:

1. Ship the token flow in your app and server.
2. Keep sending the key for a pilot until that pilot has connected through the token flow. The key keeps working until the cut-off, unless the pilot signs out everywhere, which replaces the user key.
3. Move each pilot the next time they open your app: show the connect screen, and when the pilot approves, store the tokens, switch that pilot's imports to the token route, and delete the stored user key.
4. Log when a response from the key route carries a `Deprecation` header, so you can see how many pilots have not moved yet.
5. When the cut-off date is announced, remind the pilots who are still on a key to open your app before it.

You can repeat the same payload on the token route that you sent on the key route. The entries match, and the flights you created with the key are updated, not duplicated.

## What the key route answers

A key can also stop working for reasons the token route does not have. When the pilot uses "Sign Out Everywhere" in the Jetlog app, the user key is replaced. The old key answers `401` with `invalid_user_key`, and the pilot has to copy the new key into your app. On the token route the pilot approves your app again in the Jetlog app and nothing has to be copied, which is one more reason to move pilots over. While the pilot's account is scheduled for deletion, the key route answers `403` with `{"error":"deletion_scheduled"}` and writes nothing. The same key works again if the pilot cancels the deletion. Requests with a missing or wrong key are limited to 20 per 15 minutes for each IP address. Beyond that the answer is `429` with `{"error":"rate_limited","retry_after":<seconds>}` and a `Retry-After` header. Requests with valid keys are not limited by this.

Sending the key pair to the token route is the same as sending no token: it answers `401`.

## Migration checklist

- [ ] Jetlog has linked your metadata document to your existing registration, and `client_id` in every token route request is the address of that document.
- [ ] The token flow is in your app and on your server, and follows the [checklist of the getting started guide](GETTING_STARTED.md#checklist).
- [ ] Pilots still on a key keep using it until they move, and are moved the next time they open the app.
- [ ] When a pilot connects through the token flow, that pilot's imports go to the token route and the stored user key is deleted.
- [ ] A response from the key route with a `Deprecation` header is logged, so you can see how many pilots have not moved yet.
