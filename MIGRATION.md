# Moving to token authentication

This guide is for partners that send flights to Jetlog with the key pair, `Authorization: Bearer <user_key>:<partner_key>` on `/external/v1/import`. It is also the complete description of the token flow for a partner that starts from scratch. It uses the own flights level, which gives the access the key pair gives. The wider level, with reading and proposals, is described in [PARTNER_API.md](PARTNER_API.md).

Words used in this guide:

- A **partner** is an app or service that sends flights to Jetlog on behalf of pilots.
- A **pilot** is the person whose logbook receives those flights.
- The **key route** is `POST https://jetlog.app/external/v1/import`, authenticated with the key pair.
- The **token route** is `POST https://jetlog.app/api/partner/v1/import`, authenticated with an access token the pilot approved.

Sections:

1. [What changes and what stays the same](#what-changes-and-what-stays-the-same)
2. [Key route and token route compared](#key-route-and-token-route-compared)
3. [Access levels](#access-levels)
4. [The steps](#the-steps)
5. [A phone app](#a-phone-app)
6. [A server](#a-server)
7. [Errors on the token route](#errors-on-the-token-route)
8. [Running both routes side by side](#running-both-routes-side-by-side)
9. [Checklist](#checklist)

## What changes and what stays the same

**Stays the same**

- The payload. `entries` and `people` follow the schema in the [README](README.md), with the same field rules, the same `null` handling and the same allowlists.
- Matching. An entry is matched per pilot on `date + flight_number + from + to`, exactly as on the key route.
- The response. A successful call returns `{"data": "OK", "skipped": [...]}`, plus `warnings` when there is something to report. The skip reasons are unchanged.
- On the import route a partner only ever changes entries it created. Entries written by the pilot, by a roster import or by another partner are never modified and come back as `duplicate`.
- Entries you created with the key pair stay yours after you switch. Both routes attribute flights to the same partner registration, so a token can amend or delete a flight you sent earlier with a key.

**Changes**

- The credential. You send a per-pilot access token instead of the two keys.
- The URL. `/api/partner/v1/import` instead of `/external/v1/import`.
- How a pilot connects. The pilot approves your app in the Jetlog app, instead of copying a key out of it.
- Lifetime. Access tokens last one hour and refresh tokens 90 days. The keys do not expire.
- At most 200 entries and 1000 people per request on the token route.
- The pilot does not need the external source selected in Jetlog. The connection is listed under Settings > Connected Apps and works next to a calendar or roster source the pilot has set up.
- With `scope=import`, what a token may do is what the key pair may do: add flights with their crew, and change or delete the flights your partner registration created. It cannot read the logbook or touch anything else. A wider level exists and is optional, see [Access levels](#access-levels).
- Calls on the token route do not create an import batch in the pilot's list of imports. They are recorded in the audit log.

## Key route and token route compared

| | Key route | Token route |
| :-- | :-- | :-- |
| Endpoint | `POST /external/v1/import` | `POST /api/partner/v1/import` |
| Header | `Authorization: Bearer <user_key>:<partner_key>` | `Authorization: Bearer <access_token>` |
| How a pilot connects | The pilot enables the external source in Jetlog and hands the user key to the partner | The partner starts an authorization request and the pilot approves it in the Jetlog app |
| What the partner stores | One partner key for all pilots, one user key per pilot | No shared secret. One refresh token per pilot |
| Lifetime | Neither key expires | Access token 1 hour. Refresh token 90 days, replaced on every use |
| What it may do | Add flights, change and delete the flights the partner created | The same with `scope=import`. A wider level is optional, see [Access levels](#access-levels) |
| Requests | No cap documented | At most 200 entries and 1000 people |
| Pilot's source setting in Jetlog | Must be the external source | No requirement |
| How to disconnect | The pilot changes the source in the Source screen of the Jetlog app | The partner calls the revoke endpoint, or the pilot removes the app under Settings > Connected Apps |

## Access levels

A pilot approves a partner at one of two levels. A request with `scope=import` gives the own flights level, which is exactly the access the key pair gives: add flights, and change or remove the flights the partner added. Nothing in this guide changes for a partner that asks for `scope=import`, and it is all a partner moving from the key pair needs.

The wider level is optional. It is called whole logbook, and a partner asks for it with `scope=import read write`. It adds reading the logbook and proposing changes that the pilot approves in the Jetlog app. Three things to know before asking for it:

- Jetlog enables it for each partner separately. Say so in the email of [step 2](#2-register-the-url). A partner that is not enabled gets the own flights level, whatever it asks for, and no error.
- The pilot chooses the level when approving, so a partner can receive less than it asked for. The `scope` in the token response says what was granted.
- A partner that gets `scope=import` back works exactly as described in this guide.

The routes, the proposals and their errors are in [PARTNER_API.md](PARTNER_API.md).

## The steps

In order:

1. Host a metadata document on your own domain.
2. Send its URL to Jetlog to be registered.
3. Send the pilot to Jetlog with an authorization request (authorization code with PKCE).
4. Receive the callback.
5. Exchange the code for tokens.
6. Store the tokens.
7. Call the import route, and refresh when the access token expires.
8. Disconnect with the revoke endpoint.

The endpoints:

| | URL |
| :-- | :-- |
| Authorization | `https://jetlog.app/oauth/authorize` |
| Token | `https://jetlog.app/oauth/token` |
| Revoke | `https://jetlog.app/oauth/revoke` |
| Import | `https://jetlog.app/api/partner/v1/import` |

These endpoints are also listed in the standard discovery document at `https://jetlog.app/.well-known/oauth-authorization-server`.

Two fixed values appear in every request below. The **scope** is `import`, which gives the access of the key pair. The **resource** is `https://jetlog.app/api/partner/v1`, which names the token route as the place the token is meant for. A token that was issued for another resource is refused on the token route.

Jetlog has no client secrets. Your identity is the URL of your metadata document, and PKCE protects the authorization code.

### 1. Host the metadata document

The metadata document is a JSON file served from your own domain. Its URL is your `client_id`. Jetlog fetches it to learn your name and the redirect URIs you use.

```json
{
  "client_id": "https://partner.example.com/jetlog-client.json",
  "client_name": "Example Partner",
  "client_uri": "https://partner.example.com",
  "logo_uri": "https://partner.example.com/assets/logo-256.png",
  "redirect_uris": [
    "https://partner.example.com/oauth/jetlog/callback",
    "https://api.partner.example.com/oauth/jetlog/callback"
  ]
}
```

The rules:

- It is served over `https://` on port 443, with a valid certificate. Any path works.
- The URL answers `200` directly. Redirects are not followed.
- The response is a JSON object of at most 64 KB and arrives within a few seconds (the whole fetch is cut off after 5 seconds).
- The host resolves to public addresses. A host that resolves to a private, loopback or link-local address is refused.
- `client_id` is required and equals the URL the document is served from, character for character.
- `client_name` is required. It is at most 64 characters of printable ASCII, with no control characters. Pilots see the name Jetlog registered for you in step 2, so use the same name here.
- `redirect_uris` is required and lists at least one URI of at most 255 characters. Every URI is `https://`. Plain `http://` is accepted only for `127.0.0.1`, `localhost` and `[::1]`, which is meant for development on your own computer. Custom schemes such as `partner://callback` are not accepted. See [A phone app](#a-phone-app) for why.
- `client_uri`, `logo_uri` and `software_id` are optional, at most 255 characters each. Other fields are ignored.

Jetlog keeps a copy of the document for 24 hours. After that it fetches the document again the next time an authorization request arrives. When that fetch fails, Jetlog keeps using the copy it has. Publish a change, such as a new redirect URI, at least a day before you rely on it, and keep the document available.

Put one redirect URI in the document for each place a pilot can come back to: one for the phone app, one for the server, or both.

### 2. Register the URL

Email the URL of your metadata document to support@jetlog.app, together with the name pilots should see for your partner. If your app is going to ask for the whole logbook level, say so in the same email. Jetlog links the URL to your existing partner registration, which is why flights you created with the keys stay yours. Jetlog tells you when it is done.

Until then an authorization request for your URL comes back to your callback with `error=unauthorized_client`, and no token is issued. If Jetlog ever disables a partner registration, the token route answers `403` with `integration_disabled` and a refresh answers `unauthorized_client`. Keep the tokens you hold. They work again when the registration is enabled.

### 3. Build the authorization request

Generate three values for every attempt. The code verifier and the state are random. The code challenge is the SHA-256 hash of the verifier, base64url encoded without padding.

```sh
CODE_VERIFIER=$(openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n')
CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=\n')
STATE=$(openssl rand -hex 16)
```

Keep the verifier and the state until the callback arrives. Then open this URL in a browser, with the values percent-encoded:

```sh
AUTH_URL="https://jetlog.app/oauth/authorize?response_type=code&client_id=https%3A%2F%2Fpartner.example.com%2Fjetlog-client.json&redirect_uri=https%3A%2F%2Fpartner.example.com%2Foauth%2Fjetlog%2Fcallback&scope=import&state=${STATE}&code_challenge=${CODE_CHALLENGE}&code_challenge_method=S256&resource=https%3A%2F%2Fjetlog.app%2Fapi%2Fpartner%2Fv1"
open "$AUTH_URL"    # macOS. On Linux use xdg-open.
```

| Parameter | Value |
| :-- | :-- |
| `response_type` | `code` |
| `client_id` | The URL of your metadata document |
| `redirect_uri` | One of the `redirect_uris` in the document, copied exactly |
| `scope` | `import` for the access of the key pair. `import read write` lets the pilot choose a wider level, see [Access levels](#access-levels) |
| `state` | A random value you check again on the callback |
| `code_challenge` | The S256 challenge of your verifier |
| `code_challenge_method` | `S256`. The `plain` method does not exist |
| `resource` | `https://jetlog.app/api/partner/v1` |

What the pilot sees is described in [A phone app](#a-phone-app). In short, the pilot signs in on the Jetlog page by approving in the Jetlog app, sees who is asking and what the partner may do, and approves.

The sign-in request on the page is valid for ten minutes. The page shows a countdown and offers a new code when it runs out. A pilot who has no phone with the Jetlog app at hand can choose "Use email instead" at the bottom of the page.

Approving in the app needs a current version of Jetlog. An older version shows "Update Jetlog to approve this sign-in". The pilot updates the app and tries again, or uses the email option.

### 4. Receive the callback

After the pilot approves, Jetlog redirects the browser to your `redirect_uri`:

```
https://partner.example.com/oauth/jetlog/callback?code=Zm9vYmFyYmF6cXV4&iss=https%3A%2F%2Fjetlog.app&state=c3da9a7461dc72751aad2f2784d7b213
```

Check that `state` equals the value you sent, and that `iss` is `https://jetlog.app`. Reject the callback if either differs.

When the pilot declines, or cancels, the redirect carries an error instead of a code:

```
https://partner.example.com/oauth/jetlog/callback?error=access_denied&error_description=The+user+denied+the+request&iss=https%3A%2F%2Fjetlog.app&state=c3da9a7461dc72751aad2f2784d7b213
```

Show the pilot that the connection was not made. Do not start the flow again on your own.

A redirect is not guaranteed. When the pilot denies the request in the Jetlog app, or the ten minutes run out, the Jetlog page offers "Try again" and "Cancel". Only "Cancel" redirects to your callback with `error=access_denied`. A pilot can also close the page. Treat a flow that never comes back as not connected, and let the pilot start again.

### 5. Exchange the code

The code is valid for 60 seconds and can be used once. Exchange it right away.

```sh
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=authorization_code \
  --data-urlencode "code=$CODE" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json" \
  --data-urlencode "redirect_uri=https://partner.example.com/oauth/jetlog/callback" \
  --data-urlencode "code_verifier=$CODE_VERIFIER" \
  --data-urlencode "resource=https://jetlog.app/api/partner/v1"
```

The `redirect_uri` is the same string you used in the authorization request. The endpoint also accepts a JSON body with the same fields. The `scope` in the response says what was granted. After a request with `scope=import` it is always `import`. The response:

```json
{
  "access_token": "jlp_example_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "jlr_example_refresh_token",
  "scope": "import"
}
```

Presenting a code a second time fails, and it also revokes the tokens that the first exchange issued.

### 6. Store the tokens

Store both tokens per pilot, together with the time the access token expires (`expires_in` is in seconds). Treat them like passwords: keep them out of logs, URLs and analytics, and store the refresh token in encrypted storage. Where that is on a phone and on a server is covered in the next two sections.

### 7. Call the import route

```sh
curl -sS -X POST https://jetlog.app/api/partner/v1/import \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"type":"flight","date":"2026-08-14","flight_number":"KL1023","from":"EHAM","to":"EGLL"}],"people":[]}'
```

```json
{"data": "OK", "skipped": []}
```

The body and the response are the ones described in the [README](README.md) and in [EXAMPLES.md](EXAMPLES.md). Read `skipped` and `warnings` on every response, because a `200` does not mean every row landed.

Send at most 200 entries and 1000 people per request. Include in each request the `people` its entries refer to, because a `ref_id` only has meaning inside one request.

**Refreshing.** The access token lasts one hour. Refresh a minute or so before it expires, or when a call answers `401`:

```sh
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=refresh_token \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json"
```

The response has the same shape as the code exchange:

```json
{
  "access_token": "jlp_example_second_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "jlr_example_second_refresh_token",
  "scope": "import"
}
```

A refresh token is good for one refresh. The response carries a new refresh token, which is good for 90 days from that moment. A pilot whose app goes unused for 90 days has to connect again.

Rules for refreshing:

- Save the new refresh token before you do anything else with the response. The old one no longer works.
- Run one refresh at a time per pilot. Two refreshes with the same token race, and the loser fails with `invalid_grant`.
- Never reuse an old refresh token. Presenting a refresh token that was already replaced, other than within seconds of the replacement, ends the whole connection and the pilot has to connect again.
- Give the refresh request a generous timeout. If you cannot tell whether a refresh went through, the old token may already be spent. A retry then answers `invalid_grant`, and the pilot connects again.
- `client_id` is optional on a refresh. When you send it, it has to be the same one the token was issued to.

### 8. Disconnect

When a pilot disconnects in your app, revoke the refresh token and delete what you stored:

```sh
curl -sS -i -X POST https://jetlog.app/oauth/revoke \
  -d token_type_hint=refresh_token \
  --data-urlencode "token=$REFRESH_TOKEN"
```

```
HTTP/2 200
```

The answer is `200` with an empty body, whether or not the token was still valid. Revoking the refresh token also ends the access token issued with it.

A pilot can also remove your app under Settings > Connected Apps in the Jetlog app. From then on the access token answers `401` and a refresh answers `invalid_grant`. Treat that as a disconnect: mark the pilot as not connected and offer to connect again.

## A phone app

A phone app runs the whole flow itself. The browser part runs in the system browser, never in a web view inside your app, so the pilot sees the real `jetlog.app` address and your app cannot read what the page shows.

### iOS

Use `ASWebAuthenticationSession` with an https callback. This needs iOS 17.4 or later.

```swift
import AuthenticationServices

let session = ASWebAuthenticationSession(
    url: authorizationURL,
    callback: .https(host: "partner.example.com", path: "/oauth/jetlog/callback")
) { callbackURL, error in
    guard let callbackURL else { return }   // cancelled or failed
    // Read code, state and iss from callbackURL, then exchange the code.
}
session.presentationContextProvider = contextProvider
session.start()
```

The callback host has to be associated with your app through the `webcredentials` service: an Associated Domains entitlement in the app and an `apple-app-site-association` file on that domain. Apple's documentation for `ASWebAuthenticationSession.Callback` has the exact setup.

### Android

Open the authorization URL in a Custom Tab and receive the redirect as an App Link.

```kotlin
CustomTabsIntent.Builder().build().launchUrl(context, authorizationUri)
```

```xml
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https"
        android:host="partner.example.com"
        android:path="/oauth/jetlog/callback" />
</intent-filter>
```

Serve a Digital Asset Links file at `https://partner.example.com/.well-known/assetlinks.json` so Android verifies the link.

The Jetlog app runs on Apple devices. A pilot on an Android phone approves from an iPhone or iPad that has Jetlog: the Jetlog page shows a QR code, and the pilot scans it with that device.

### Why the redirect is a claimed https link

The redirect URI of a phone app is an https link that your app has claimed (a universal link on iOS, an App Link on Android). A custom scheme such as `partner://callback` is not accepted. On iOS, any app can register the same scheme, and the system may hand your authorization code to the wrong app. A claimed https link is tied to your domain, so only your app receives it. Serve a useful page at that URL as well, because a phone without your app lands there.

### What the pilot sees on the same phone

1. Your app opens the Jetlog page in the system browser sheet. The page is titled "Sign in with the Jetlog app". It shows your name, a two digit number, a QR code, and an "Open in Jetlog" button.
2. The pilot remembers the number and taps "Open in Jetlog". The Jetlog app opens an approval screen. For a request with `scope=import` it names your app, says what your app may do, which is add flights and their crew and change or remove the flights it added, and says what it may not do, which is read the logbook or change anything else. For a request that asks for the whole logbook level it offers the pilot a choice between that level and your own flights only. It also shows three numbers.
3. The pilot taps the number that matches the one on the page and confirms with Face ID or the passcode. A wrong number blocks the request.
4. The pilot switches back to your app, where the browser sheet is still open. The page now says the request was approved in the Jetlog app and names the account. The pilot taps "Continue".
5. Jetlog redirects to your https callback. The system closes the sheet and passes the URL to your app, which exchanges the code.

If the pilot denies the request or the ten minutes run out, the page says so and offers a new attempt, or cancel, which returns `error=access_denied` to your callback.

### Where to keep the tokens

On iOS keep them in the Keychain. Use `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` if you sync in the background, so the items can be read after the first unlock and do not end up in a backup. On Android use storage backed by the Android Keystore. Do not keep tokens in preferences, files or databases in plain text.

### Refresh tokens rotate

Every refresh replaces the refresh token, so refreshes must not run concurrently. Route every call through one component that owns the token pair, takes a lock around the refresh, and writes the new refresh token to secure storage before it returns. If your app also refreshes from an extension or a background task, those take the same lock, or only one of them refreshes.

## A server

A server uses the ordinary web flow.

- The callback is a normal https endpoint on your domain, for example `https://api.partner.example.com/oauth/jetlog/callback`. List it in the metadata document.
- When you start a connection, create `state` and the code verifier on the server, store them against the pilot's session, and send the pilot to the authorization URL. On the callback, look up the pilot by `state`, compare `iss`, and exchange the code with the stored verifier within 60 seconds.
- Store the refresh token per pilot in encrypted storage, and the access token with its expiry. Never send either to a browser or a mobile client that does not need it.
- Background sync works from these tokens without the pilot present. Before each sync, take a per-pilot lock, refresh if the access token is within a minute of expiring, store the new refresh token, release the lock, then import.
- When a refresh answers `invalid_grant`, stop syncing for that pilot, mark the pilot as disconnected, and ask the pilot to connect again the next time they open your app.
- When a pilot disconnects in your settings, revoke the refresh token and delete the stored tokens.

A pilot who uses your phone app and your server needs one holder of the refresh token. Either the server holds it, and the phone app connects through your server's callback, or the phone app holds it and calls Jetlog directly. Do not copy one refresh token to a second place, because the first refresh in either place makes the other copy useless.

## Errors on the token route

| Status | Body | Meaning | What to do |
| :-- | :-- | :-- | :-- |
| `401` | `{"error":"invalid_token"}` and `WWW-Authenticate: Bearer error="invalid_token"` | The token is missing, unknown, expired, revoked, or meant for another resource | Refresh once and repeat the request once. If the refresh fails with `invalid_grant`, the pilot must connect again |
| `403` | `{"error":"integration_disabled"}` | Jetlog has disabled your partner registration | Stop sending. Email support@jetlog.app |
| `403` | `{"error":"insufficient_scope"}` | The token does not carry the `import` scope | The pilot connects again with `scope=import` |
| `413` | `{"error":"too_many_entries","max":200}` | More than 200 entries in one request | Split the payload into requests of at most 200 entries. Nothing was written |
| `413` | `{"error":"too_many_people","max":1000}` | More than 1000 people in one request | Send only the people the entries in that request refer to. Nothing was written |
| `429` | A `Retry-After` header, in seconds, and `{"error":"rate_limited","retry_after":n}` | Too many requests for this pilot | Wait for `Retry-After`, then send the same request. Send one pilot's imports one after another |
| `400` | `{"error":"<code>"}`, for example `invalid_payload` | The payload could not be imported as a whole | Fix the payload. Nothing was written |
| `400` for a body that is not valid JSON, and any `5xx` | `{"errors":{"detail":"<status text>"}}` | The request could not be read, or something failed on the Jetlog side | Fix the request body. After a `5xx`, resend the same payload. It is safe, because matching applies the same rows again |

Resending a payload is always safe. Entries that already exist are matched and updated, not duplicated, and people that were created by an earlier attempt match on the retry.

Sending the key pair to the token route is the same as sending no token: it answers `401`.

On the authorization and token endpoints:

| Where | What you get | Meaning |
| :-- | :-- | :-- |
| Authorization, browser shows a Jetlog error page | No redirect to your callback | Jetlog could not trust the request: the metadata document is unreachable or invalid, `redirect_uri` is not in the document, or a required parameter is missing |
| Authorization, redirect with `error=unauthorized_client` | Your metadata document URL is not registered with Jetlog, or the registration is disabled | Register the URL (step 2), or email support@jetlog.app |
| Authorization, redirect with `error=access_denied` | The pilot declined or cancelled | Show that nothing was connected |
| Authorization, redirect with `error=invalid_request`, `unsupported_response_type` or `invalid_target` | A parameter is wrong | `code_challenge_method` has to be `S256`, `response_type` has to be `code`, `resource` has to be `https://jetlog.app/api/partner/v1` |
| Token, `400` `{"error":"invalid_grant"}` on a code | The code expired (60 seconds), was already used, or something does not match: `client_id`, `redirect_uri`, `code_verifier` or `resource` | Start the authorization again |
| Token, `400` `{"error":"invalid_grant"}` on a refresh | The refresh token is unknown, already used, expired, or revoked, or the pilot disconnected or signed out everywhere | The pilot connects again |
| Token, `400` `{"error":"unauthorized_client"}` on a refresh | Jetlog has disabled your partner registration | Keep the stored tokens and stop syncing. Email support@jetlog.app. The same refresh token works again once the registration is enabled |
| Token, `400` `{"error":"invalid_request"}` or `{"error":"unsupported_grant_type"}` | `grant_type` is missing or not one of `authorization_code` and `refresh_token` | Fix the request |
| Token or revoke, `429` | A `Retry-After` header and `{"error":"rate_limited","retry_after":n}` | Wait, then try again |

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
2. Keep sending the key for a pilot until that pilot has connected through the token flow. The key keeps working until the cut-off.
3. Move each pilot the next time they open your app: show the connect screen, and when the pilot approves, store the tokens, switch that pilot's imports to the token route, and delete the stored user key.
4. Log when a response from the key route carries a `Deprecation` header, so you can see how many pilots have not moved yet.
5. When the cut-off date is announced, remind the pilots who are still on a key to open your app before it.

You can repeat the same payload on the token route that you sent on the key route. The entries match, and the flights you created with the key are updated, not duplicated.

## Checklist

- [ ] The metadata document is served over https, answers `200` without redirects, and its `client_id` equals its own URL.
- [ ] `client_name` is printable ASCII of at most 64 characters, and every redirect URI is https.
- [ ] The URL is sent to support@jetlog.app and confirmed as registered.
- [ ] Every authorization request has a fresh `state` and a fresh S256 code challenge, and carries the `scope` your app needs (`import` for the access of the key pair) and `resource=https://jetlog.app/api/partner/v1`.
- [ ] The callback checks `state` and `iss`, and handles `error=access_denied`.
- [ ] The code is exchanged within 60 seconds, with the same `redirect_uri` and the stored verifier.
- [ ] Phone app: system browser, https callback that the app has claimed, no custom scheme.
- [ ] Tokens live in the Keychain, the Android Keystore or encrypted server storage, and not in logs.
- [ ] One refresh at a time per pilot, and the new refresh token is saved before the response is used.
- [ ] A `401` triggers one refresh and one retry. A failed refresh moves the pilot to "not connected".
- [ ] Requests have at most 200 entries and 1000 people, include the `people` they refer to, and wait out `Retry-After` on a `429`.
- [ ] `skipped` and `warnings` are read on every response.
- [ ] Disconnecting calls the revoke endpoint and deletes the stored tokens.
- [ ] Pilots still on a key keep using it until they move, and are moved the next time they open the app.
