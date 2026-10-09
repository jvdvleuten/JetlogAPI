# Moving to token authentication

This guide is for partners that send flights to Jetlog with the key pair, `Authorization: Bearer <user_key>:<partner_key>` on `/external/v1/import`. It is also the complete description of the token flow for an app that starts from scratch. A new app registers in the developer console (step 1), and a partner that already uses the key pair does not: it asks Jetlog to link its metadata document to its existing registration. This guide uses the own flights level, which gives the access the key pair gives. The wider level, with reading and proposals, is described in [PARTNER_API.md](PARTNER_API.md).

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
- With `scope=import`, what a token may do is what the key pair may do: add flights with their crew, and change or delete the flights your partner registration created. It cannot read the logbook or touch anything else. A wider level exists and is optional, see [Access levels](#access-levels).
- Calls on the token route do not create an import batch in the pilot's list of imports. They are recorded in the audit log.

## Key route and token route compared

| | Key route | Token route |
| :-- | :-- | :-- |
| Endpoint | `POST /external/v1/import` | `POST /api/partner/v1/import` |
| Header | `Authorization: Bearer <user_key>:<partner_key>` | `Authorization: Bearer <access_token>` |
| How a pilot connects | The pilot enables the external source in Jetlog and hands the user key to the partner | The partner starts an authorization request and the pilot approves it in the Jetlog app |
| What the partner stores | One partner key for all pilots, one user key per pilot | No shared secret. One refresh token per pilot |
| Lifetime | Neither key expires | Access token 1 hour. Refresh token 90 days. An app with a client secret keeps the same refresh token, an app without one gets a new one on every use |
| When the pilot signs out everywhere | The user key is replaced and the pilot copies the new key into your app | The connection ends and the pilot approves your app again in the Jetlog app |
| What it may do | Add flights, change and delete the flights the partner created | The same with `scope=import`. A wider level is optional, see [Access levels](#access-levels) |
| Requests | No cap documented | At most 200 entries, 1000 people and 2 MB |
| Pilot's source setting in Jetlog | Must be the external source | No requirement |
| How to disconnect | The pilot changes the source in the Source screen of the Jetlog app | The partner calls the revoke endpoint, or the pilot removes the app under Settings > Connected Apps |

## Access levels

A pilot approves a partner at one of two levels. A request with `scope=import` gives the own flights level, which is exactly the access the key pair gives: add flights, and change or remove the flights the partner added. Nothing in this guide changes for a partner that asks for `scope=import`, and it is all a partner moving from the key pair needs.

The wider level is optional. It is called whole logbook, and a partner asks for it with `scope=import read write`. It adds reading the logbook and proposing changes that the pilot approves in the Jetlog app. Three things to know before asking for it:

- It is available only to an app that has all of these: the access switched on by Jetlog, a client secret, approved redirect addresses, and no loopback address (`localhost`, `127.0.0.1` or `[::1]`) among them. A new app asks for the access on its own page in the developer console once it is approved, and generates its client secret on the same page, see [step 2](#2-review-development-and-the-client-secret). An app that runs on the pilot's own computer therefore works at the own flights level. An app that does not meet these gets the own flights level, whatever it asks for, and no error. While an app is waiting for review, its developer's own account can use the whole logbook level without Jetlog's switch and without approved addresses, as long as the app has a client secret and no loopback address, see [step 2](#2-review-development-and-the-client-secret).
- The pilot chooses the level when approving, so a partner can receive less than it asked for. The `scope` in the token response says what was granted.
- A partner that gets `scope=import` back works exactly as described in this guide.

The routes, the proposals and their errors are in [PARTNER_API.md](PARTNER_API.md).

## The steps

In order:

1. Register your app in the developer console, with a form or with a metadata document on your own domain. A partner that already uses the key pair has Jetlog link its document to its existing registration instead.
2. Build and test while Jetlog reviews the app, and set up the client secret and the redirect addresses.
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

These endpoints are also listed in the standard discovery document at `https://jetlog.app/.well-known/oauth-authorization-server`. It lists `client_secret_post` next to `none` as the ways to authenticate at the token endpoint. `client_secret_post` is the one for an app that has a client secret.

Two fixed values appear in every request below. The **scope** is `import`, which gives the access of the key pair. The **resource** is `https://jetlog.app/api/partner/v1`, which names the token route as the place the token is meant for. A token that was issued for another resource is refused on the token route.

Your identity is your `client_id`: the app id the console gave you, or, for an app registered with a metadata document, the URL of that document. PKCE protects the authorization code. An app can also have a client secret, which its developer generates in the developer console, see [step 2](#2-review-development-and-the-client-secret). An app without a secret works exactly as described in this guide.

The examples below show the URL of the example metadata document as `client_id`. An app registered with the form puts its app id there, and everything else in the examples stays the same.

### 1. Register your app

A new app registers in the developer console. The page for developers is `https://jetlog.app/developers` and the console is `https://jetlog.app/developers/console`. You need a Jetlog account for this, and the console does not create one. The console signs you in with the Jetlog app: it shows a QR code and a number, and you approve the sign-in in the app. Without the app at hand you can choose email instead, and Jetlog mails a code to the address of your account.

There are two ways to register, and both give the same kind of app. The form is the simplest, and nothing has to be hosted. The metadata document is for developers who prefer to describe the app in a file on their own domain.

#### With a form

The form asks for two things:

- The name pilots will see for your app. The name is 2 to 64 printable ASCII characters. It cannot read as "Jetlog", also not with spaces, dashes or look-alike letters, it cannot contain `/`, `:`, `@`, `<` or `>`, it cannot start with `www.`, and it has to be a name no other approved app uses.
- The redirect addresses, one on each line. These are the places where Jetlog sends the pilot back to your app. Give at least 1 and at most 10, none twice. Every address is `https://` and at most 255 characters. Plain `http://` is accepted only for `127.0.0.1`, `localhost` and `[::1]`, which is meant for development on your own computer. Custom schemes such as `partner://callback` are not accepted. See [A phone app](#a-phone-app) for why. Each address is a plain address with an ordinary ASCII host name: no backslash, no `user@` part or `%` in the host, no spaces, and no `#` fragment.

Submit the form. The console answers with the page of your app, which shows its **app id**. The app id is your `client_id`. Copy it from that page into your app and use it in every request below. It looks like this:

```
jetlog_app_VUGENuUg7Q6UL-CGr67N8aEz5Q_ZvwfKxWeBYz0Bd9s
```

Jetlog generates the app id, so you do not choose it. The name cannot be changed after submitting. To change it, register a new app, or write to support@jetlog.app. The redirect addresses can be changed on the app's page, see [step 2](#2-review-development-and-the-client-secret).

#### With a metadata document

Instead of the form you can describe your app in a metadata document, a JSON file served from your own domain. Its URL is your `client_id`. Jetlog fetches it to learn your name and the redirect URIs you use.

```json
{
  "client_id": "https://partner.example.com/jetlog-client.json",
  "client_name": "Example Partner",
  "jetlog_developer": "jld_m4zq7vtn2xkc5hbdr3wypfa6e7",
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
- `client_name` is required. It is at most 64 characters of printable ASCII, with no control characters. It cannot read as "Jetlog": not in any letter case, and not with spaces, dashes, a digit or a capital I in place of a letter. Pilots see the name you register, which can differ from this one, so use the same name here.
- `jetlog_developer` is the verification value that the developer console shows you, a top-level string that starts with `jld_`. An app registered in the console with a document must carry it. It is the same for every app of one developer. It is not a secret and not a key. It only shows that the document is yours, so it is fine that it sits in a public file. A partner that already uses the key pair and has its document linked by Jetlog does not need it.
- `redirect_uris` is required and lists at least one URI of at most 255 characters. Every URI is `https://`. Plain `http://` is accepted only for `127.0.0.1`, `localhost` and `[::1]`, which is meant for development on your own computer. Custom schemes such as `partner://callback` are not accepted. See [A phone app](#a-phone-app) for why. Each URI is a plain address with an ordinary ASCII host name: no backslash, no `user@` part or `%` in the host, no spaces, and no `#` fragment.
- `client_uri`, `logo_uri` and `software_id` are optional, at most 255 characters each. Other fields are ignored.

Jetlog keeps a copy of the document for 24 hours. After that it fetches the document again the next time an authorization request arrives. When that fetch fails, Jetlog keeps using the copy it has. Publish a change at least a day before you rely on it, and keep the document available. A new or changed redirect URI also needs Jetlog's approval before it works, see [step 2](#2-review-development-and-the-client-secret).

Put one redirect URI in the document for each place a pilot can come back to: one for the phone app, one for the server, or both.

To register the document:

1. The console shows your verification value, which starts with `jld_`. Put it in your metadata document as the top-level field `jetlog_developer`, as in the example above. The value is the same for every app you register. It is not a secret and not a key.
2. Fill in the second registration form on the page, the one under "Or host a metadata document". Give the name pilots will see for your app, with the same rules as in the form above, and the address of your metadata document, which is your `client_id`.
3. Press "Check document". Jetlog fetches the document, checks it by the rules above and checks your verification value, and lists every problem in plain words. Submitting runs the same check again.
4. Submit the registration. From then on the name and the address cannot be changed. To change them, register a new app, or write to support@jetlog.app.

**A partner that already uses the key pair does not register in the console.** Write to support@jetlog.app with the address of your metadata document, and Jetlog links that address to your existing partner registration. This is why flights you created with the keys stay yours. Jetlog tells you when it is done. For a linked document the `jetlog_developer` field is not needed.

Limits: you can have at most 5 apps, rejected ones not counted, and submit at most 5 registrations in 24 hours, withdrawn and rejected ones included. A registration that is still in review can be withdrawn on its page.

### 2. Review, development and the client secret

Jetlog reviews every app and you get an email with the decision. Jetlog approves the name and the redirect addresses it sees at that moment: for an app registered with the form the ones on the app's page, and for an app registered with a document the redirect URIs in the document, which Jetlog fetches again before approving, so the document must still carry your verification value then. If your app is not approved, its page in the console shows a note with the reason.

**Building before approval.** An app that is waiting for review already works for your own Jetlog account, so you can build and test straight away. Use your `client_id` and one of your redirect addresses in the authorization request of [step 3](#3-build-the-authorization-request) and go through the steps below as any app does. The Jetlog sign-in pages say that the app is in development and has not been reviewed. The flights your app sends are written to your own logbook like any other. A pilot who is not you cannot connect the app until Jetlog has approved it, and nothing is issued for that pilot. Until the redirect addresses are approved, the addresses of the app, on its page in the console or in its document, are the ones it can use, for your account only. When Jetlog approves the app, the connections you made keep working with the same tokens, and any pilot can connect it. When Jetlog rejects the app, or you withdraw it, your test connections stop with the next request.

You can also try the whole logbook level in development, without waiting for Jetlog to switch it on. It needs a client secret, which you can generate while the app is waiting, and no loopback address among the redirect addresses. The own flights level has no such conditions.

**Changing the redirect addresses.** For an app registered with the form, change the addresses on the app's page in the console, with the same rules as when registering. For an approved app, a new address works once Jetlog has approved it, and Jetlog is told when you save. An address you remove stops working at once. You can save changes up to 20 times a day for each app. An app registered with a document changes its addresses in the document instead, and writes to support@jetlog.app to have a new or changed address approved. An authorization request with a redirect URI that is not approved gets the Jetlog error page, like any other redirect URI that is not listed for the app.

**Confirming a change.** Generating a client secret and changing the redirect addresses ask for a confirmation first, because either one decides who can act as your app, and nobody who borrows your signed-in browser should be able to do that. The sections for the secret and the addresses on the app's page show a button, "Confirm with an emailed code to make changes". Jetlog mails a code to the email address of your Jetlog account, never to another address. The code is valid for 10 minutes. After you enter it, the secret and the addresses can be changed for 10 minutes. Signing in to the console does not count as a confirmation.

When your app needs the whole logbook level, ask for it on the app's page in the console once the app is approved. Give a short reason, 10 to 500 characters, that says which data you read and why. Jetlog decides per app and emails the decision. The page shows the result. Without it, your app gets the own flights level. When the access is switched on but cannot be used yet, the page says why: no client secret is set, no redirect addresses are approved, or an approved redirect address is a loopback address.

**The client secret.** An approved app, and an app that is waiting for review, has a button on its page in the console to generate a client secret, after the confirmation above. Jetlog shows the secret once, so copy it then and keep it on your server, never in a mobile app or a web page. Generating a new secret replaces the old one at once, Jetlog emails you each time, and you can generate one at most 5 times a day. From the moment an app has a secret, every request to the token endpoint for it must carry the secret as `client_secret` in the body, for the code exchange and for every refresh, see [step 5](#5-exchange-the-code). A pilot who is already connected stays connected: the next refresh with the secret keeps the refresh token your app holds. The whole logbook level needs a secret. An app without one works as described in this guide.

The app's page in the console shows the app id of an app registered with the form, the status of the review, the redirect addresses, which access is enabled, how many pilots have connected the app (a count, never who), the requests of the last 30 days per day split into import, read and changes, the errors your app got, and how often the rate limit stopped it. The statistics start once pilots use the app.

A pilot who approves your app in the Jetlog app sees the name you registered with. For an app registered with a document, the page adds the text "Registered with Jetlog under this name", and the host of your metadata document as a plain detail.

If Jetlog ever disables a partner registration, the token route answers `403` with `integration_disabled` and a refresh answers `unauthorized_client`. Keep the tokens you hold. They work again when the registration is enabled. An authorization request for a disabled app shows the pilot a Jetlog error page with `unauthorized_client`.

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
| `client_id` | The app id from the developer console, or the URL of your metadata document |
| `redirect_uri` | One of the redirect addresses you registered, or one of the `redirect_uris` in your document, copied exactly |
| `scope` | `import` for the access of the key pair. `import read write` lets the pilot choose a wider level, see [Access levels](#access-levels) |
| `state` | A random value you check again on the callback |
| `code_challenge` | The S256 challenge of your verifier |
| `code_challenge_method` | `S256`. The `plain` method does not exist |
| `resource` | `https://jetlog.app/api/partner/v1` |

A problem with the request itself shows the pilot a Jetlog error page with the error code and the status `400`. That covers a wrong `response_type`, a missing or wrong PKCE parameter, a wrong `resource`, and an app that is not registered for the partner API or is disabled. The browser is not sent to your `redirect_uri` then. Jetlog sends the browser back to your app only after the pilot has approved, denied or cancelled.

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

A pilot whose account is scheduled for deletion cannot approve a connection. The page says so with the status `403`, and the browser is not sent back to your app. The pilot can cancel the deletion in the Jetlog app and connect again.

### 5. Exchange the code

The code is valid for 60 seconds and can be used once. Exchange it right away.

```sh
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=authorization_code \
  --data-urlencode "code=$CODE" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json" \
  --data-urlencode "redirect_uri=https://partner.example.com/oauth/jetlog/callback" \
  --data-urlencode "code_verifier=$CODE_VERIFIER" \
  --data-urlencode "resource=https://jetlog.app/api/partner/v1" \
  --data-urlencode "client_secret=$CLIENT_SECRET"
```

The last parameter, `client_secret`, is for an app that has a client secret. An app without one leaves it out. When the app has a secret and the request has none, or a wrong one, the answer is `401` with `{"error":"invalid_client"}`. That request does not use up the code, so repeat it with the right secret within the 60 seconds. HTTP Basic authentication is not supported: the secret goes in the body.

The `client_id` and the `redirect_uri` are the same strings you used in the authorization request. The endpoint also accepts a JSON body with the same fields. The `scope` in the response says what was granted. After a request with `scope=import` it is always `import`. The response:

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

When the exchange succeeds, Jetlog emails the pilot that your app was connected, with the name of the app and the level the pilot granted. The pilot can remove the app under Settings > Connected Apps.

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

Send at most 200 entries and 1000 people per request, in a body of at most 2 MB. Include in each request the `people` its entries refer to, because a `ref_id` only has meaning inside one request.

**Refreshing.** The access token lasts one hour. Refresh a minute or so before it expires, or when a call answers `401`:

```sh
# An app without a client secret leaves out the last line.
curl -sS -X POST https://jetlog.app/oauth/token \
  -d grant_type=refresh_token \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=https://partner.example.com/jetlog-client.json" \
  --data-urlencode "client_secret=$CLIENT_SECRET"
```

The response has the same shape as the code exchange. The example sends a client secret, so the response carries the refresh token that was sent:

```json
{
  "access_token": "jlp_example_second_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "jlr_example_refresh_token",
  "scope": "import"
}
```

What comes back as `refresh_token` depends on whether your app has a client secret. Either way the refresh token is good for 90 days from that moment, and a pilot whose app goes unused for 90 days has to connect again.

- An app that sends its client secret keeps one refresh token for the life of the connection. Each refresh answers with a new access token and the same refresh token. The access tokens from earlier refreshes stay valid until their own hour is up. Refreshes can therefore run in parallel: two workers that refresh at the same moment both end up with a working access token, and a response that never arrives cannot cost you the connection.
- An app without a client secret gets a new refresh token with every refresh and must store it each time. The old refresh token stops working, and so does the access token that came with it.

Rules for refreshing:

- Save the refresh token from the response before you do anything else with it. For an app with a client secret it is the one you sent. For an app without one it is a new token.
- An app without a client secret runs one refresh at a time per pilot. Two refreshes with the same token race, and the loser fails with `invalid_grant`.
- Never use a refresh token that was replaced. Presenting one, other than within seconds of the replacement, ends the whole connection and the pilot has to connect again.
- Give the refresh request a generous timeout. An app without a client secret that cannot tell whether a refresh went through may find the old token already spent. A retry then answers `invalid_grant`, and the pilot connects again. An app with a client secret can send the same refresh again.
- `client_id` is optional on a refresh. When you send it, it has to be the same one the token was issued to.
- An app that has a client secret sends it with every refresh, as in the example. Without it, or with a wrong one, the answer is `401` with `{"error":"invalid_client"}`. That request does not use up the refresh token, so repeat it with the right secret.

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

The answer is `200` with an empty body, whether or not the token was still valid. Revoking any refresh token of the connection, or its current access token, ends the whole connection: every access token and refresh token of it stops working, and the proposals of the connection that were still open are marked `revoked`.

A pilot can also remove your app under Settings > Connected Apps in the Jetlog app. From then on the access token answers `401` and a refresh answers `invalid_grant`. Treat that as a disconnect: mark the pilot as not connected and offer to connect again.

## A phone app

A phone app runs the whole flow itself. The browser part runs in the system browser, never in a web view inside your app, so the pilot sees the real `jetlog.app` address and your app cannot read what the page shows.

A phone app has no safe place for a client secret, so a phone app that talks to Jetlog directly works at the own flights level, without a secret. An app that needs the whole logbook has its server hold the secret and do the code exchange and the refreshes, see [A server](#a-server).

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

A phone app works without a client secret, so every refresh replaces the refresh token, and refreshes must not run concurrently. Route every call through one component that owns the token pair, takes a lock around the refresh, and writes the new refresh token to secure storage before it returns. If your app also refreshes from an extension or a background task, those take the same lock, or only one of them refreshes.

## A server

A server uses the ordinary web flow.

- The callback is a normal https endpoint on your domain, for example `https://api.partner.example.com/oauth/jetlog/callback`. List it in the metadata document.
- When you start a connection, create `state` and the code verifier on the server, store them against the pilot's session, and send the pilot to the authorization URL. On the callback, look up the pilot by `state`, compare `iss`, and exchange the code with the stored verifier within 60 seconds.
- Store the refresh token per pilot in encrypted storage, and the access token with its expiry. Never send either to a browser or a mobile client that does not need it.
- Keep the client secret, when the app has one, on the server too, and send it as `client_secret` with every code exchange and every refresh.
- Background sync works from these tokens without the pilot present. Before each sync, refresh if the access token is within a minute of expiring and store what comes back. An app without a client secret takes a per-pilot lock around that refresh and writes the new refresh token before it releases the lock. An app with a client secret gets the same refresh token back and can refresh from several workers at once.
- When a refresh answers `invalid_grant`, stop syncing for that pilot, mark the pilot as disconnected, and ask the pilot to connect again the next time they open your app.
- When a pilot disconnects in your settings, revoke the refresh token and delete the stored tokens.

A pilot who uses your phone app and your server needs one holder of the refresh token. Either the server holds it, and the phone app connects through your server's callback, or the phone app holds it and calls Jetlog directly. Do not copy one refresh token to a second place. When the app has no client secret, the first refresh in either place makes the other copy useless.

## Errors on the token route

| Status | Body | Meaning | What to do |
| :-- | :-- | :-- | :-- |
| `401` | `{"error":"invalid_token"}` and `WWW-Authenticate: Bearer error="invalid_token"` | The token is missing, unknown, expired, revoked, or meant for another resource | Refresh once and repeat the request once. If the refresh fails with `invalid_grant`, the pilot must connect again |
| `403` | `{"error":"integration_disabled"}` | Jetlog has disabled your partner registration | Stop sending. Email support@jetlog.app |
| `403` | `{"error":"insufficient_scope"}` | The token does not carry the `import` scope | The pilot connects again with `scope=import` |
| `413` | `{"error":"too_many_entries","max":200}` | More than 200 entries in one request | Split the payload into requests of at most 200 entries. Nothing was written |
| `413` | `{"error":"too_many_people","max":1000}` | More than 1000 people in one request | Send only the people the entries in that request refer to. Nothing was written |
| `413` | `{"error":"payload_too_large","max_bytes":2097152}` | The body is larger than 2 MB. It is checked from the `Content-Length` header before anything else, so it can come before the token check | Split the payload into smaller requests. Nothing was written |
| `429` | A `Retry-After` header, in seconds, and `{"error":"rate_limited","retry_after":n}` | Too many requests for this pilot | Wait for `Retry-After`, then send the same request. Send one pilot's imports one after another |
| `400` | `{"error":"<code>"}`, for example `invalid_payload` | The payload could not be imported as a whole | Fix the payload. Nothing was written |
| `400` for a body that is not valid JSON, and any `5xx` | `{"errors":{"detail":"<status text>"}}` | The request could not be read, or something failed on the Jetlog side | Fix the request body. After a `5xx`, resend the same payload. It is safe, because matching applies the same rows again |

Resending a payload is always safe. Entries that already exist are matched and updated, not duplicated, and people that were created by an earlier attempt match on the retry.

Sending the key pair to the token route is the same as sending no token: it answers `401`.

On the authorization and token endpoints:

| Where | Meaning | What to do |
| :-- | :-- | :-- |
| Authorization, the pilot sees a Jetlog error page with `invalid_client` and the status `400` | No redirect to your callback. Jetlog could not trust the request: the `client_id` is not known, the metadata document is unreachable or invalid (a `client_name` that reads as "Jetlog" is invalid), `redirect_uri` is not one of the app's redirect addresses or not approved, or a required parameter is missing | Fix the `client_id`, the document or the request |
| Authorization, the pilot sees a Jetlog error page with `unauthorized_client` and the status `400` | No redirect to your callback. Your app was not approved, was withdrawn, or its registration is disabled. A key pair partner whose document is not linked yet gets this too | Check the status on the app's page in the developer console (step 2). A key pair partner writes to support@jetlog.app |
| Authorization, the sign-in pages say the app is in development, and the pilot cannot approve | Nothing is issued and there is no redirect. Your app is waiting for review and the pilot is not its developer | Only the developer's own Jetlog account can connect the app until Jetlog has approved it |
| Authorization, the pilot sees a Jetlog error page with `invalid_request`, `unsupported_response_type` or `invalid_target` and the status `400` | No redirect to your callback. A parameter is wrong | `code_challenge` has to be present and `code_challenge_method` has to be `S256`, `response_type` has to be `code`, `resource` has to be `https://jetlog.app/api/partner/v1` |
| Authorization, redirect with `error=access_denied` | The pilot declined or cancelled | Show that nothing was connected |
| Authorization, redirect with `error=unauthorized_client` or `error=invalid_scope` | Your registration was disabled, or your app stopped meeting the conditions of the whole logbook level, while the pilot was deciding | Show that nothing was connected. Check the app's page in the developer console |
| Authorization, the pilot sees "Account scheduled for deletion" and the status `403` | No redirect to your callback. The pilot's account is scheduled for deletion | Show that nothing was connected. The pilot can cancel the deletion in the Jetlog app and connect again |
| Token, `401` `{"error":"invalid_client"}` | Your app has a client secret, and the request has none or a wrong one | Send `client_secret` in the body and repeat the same request. The code or refresh token has not been used up |
| Token, `400` `{"error":"invalid_grant"}` on a code | The code expired (60 seconds), was already used, or something does not match: `client_id`, `redirect_uri`, `code_verifier` or `resource` | Start the authorization again |
| Token, `400` `{"error":"invalid_grant"}` on a refresh | The refresh token is unknown, already replaced, expired, or revoked, or the pilot disconnected, signed out everywhere or scheduled the account for deletion | The pilot connects again |
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

A key can also stop working for reasons the token route does not have. When the pilot uses "Sign Out Everywhere" in the Jetlog app, the user key is replaced. The old key answers `401` with `invalid_user_key`, and the pilot has to copy the new key into your app. On the token route the pilot approves your app again in the Jetlog app and nothing has to be copied, which is one more reason to move pilots over. While the pilot's account is scheduled for deletion, the key route answers `403` with `{"error":"deletion_scheduled"}` and writes nothing. The same key works again if the pilot cancels the deletion. Requests with a missing or wrong key are limited to 20 per 15 minutes for each IP address. Beyond that the answer is `429` with `{"error":"rate_limited","retry_after":<seconds>}` and a `Retry-After` header. Requests with valid keys are not limited by this.

What to do with pilots who are still on a key:

1. Ship the token flow in your app and server.
2. Keep sending the key for a pilot until that pilot has connected through the token flow. The key keeps working until the cut-off, unless the pilot signs out everywhere, which replaces the user key.
3. Move each pilot the next time they open your app: show the connect screen, and when the pilot approves, store the tokens, switch that pilot's imports to the token route, and delete the stored user key.
4. Log when a response from the key route carries a `Deprecation` header, so you can see how many pilots have not moved yet.
5. When the cut-off date is announced, remind the pilots who are still on a key to open your app before it.

You can repeat the same payload on the token route that you sent on the key route. The entries match, and the flights you created with the key are updated, not duplicated.

## Checklist

- [ ] The app is registered in the developer console and approved, and `client_id` in every request is the app id from the console or the address of the metadata document. A key pair partner has its document linked by Jetlog.
- [ ] A metadata document is served over https, answers `200` without redirects, its `client_id` equals its own URL, and it carries the `jetlog_developer` value.
- [ ] `client_name` of a document is printable ASCII of at most 64 characters, and every redirect URI is https.
- [ ] A new or changed redirect URI is approved by Jetlog before it is used.
- [ ] Every authorization request has a fresh `state` and a fresh S256 code challenge, and carries the `scope` your app needs (`import` for the access of the key pair) and `resource=https://jetlog.app/api/partner/v1`.
- [ ] The callback checks `state` and `iss`, and handles `error=access_denied`.
- [ ] The code is exchanged within 60 seconds, with the same `redirect_uri` and the stored verifier.
- [ ] An app with a client secret keeps it on its server and sends it as `client_secret` with the code exchange and with every refresh.
- [ ] Phone app: system browser, https callback that the app has claimed, no custom scheme.
- [ ] Tokens live in the Keychain, the Android Keystore or encrypted server storage, and not in logs.
- [ ] The refresh token from every response is saved before the response is used. An app without a client secret also runs one refresh at a time per pilot.
- [ ] A `401` triggers one refresh and one retry. A failed refresh moves the pilot to "not connected".
- [ ] Requests have at most 200 entries, 1000 people and 2 MB of body, include the `people` they refer to, and wait out `Retry-After` on a `429`.
- [ ] `skipped` and `warnings` are read on every response.
- [ ] Disconnecting calls the revoke endpoint and deletes the stored tokens.
- [ ] Pilots still on a key keep using it until they move, and are moved the next time they open the app.
