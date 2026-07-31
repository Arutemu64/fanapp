# ADR-0012: One OAuth callback per provider, with identity keyed on the OIDC subject

- **Status:** Accepted
- **Date:** 2026-07-31
- **Deciders:** Backend + frontend

## Context

Telegram login was built as two independent, structurally identical flows: a
login pair (`/auth/login/telegram`, `.../callback`) and an account-linking pair
(`/me/connections/telegram`, `.../callback`). Which flow a callback belonged to
was decided **solely by which URL Telegram redirected to**.

That turned out to enforce nothing. Authlib keys its state payload by *provider
name*, not by route — `StarletteIntegration.get_state_data` reads
`session["_state_telegram_{state}"]`. A state minted by the link start resolves
just as happily inside the login callback, and the `redirect_uri` Authlib replays
to the token endpoint is the one recorded in that state, so the exchange
succeeds. The two callbacks were interchangeable given a valid state; the path
was a convention, not a boundary. Nothing bound the flow's *intent* to anything.

Separately, `social_identities.provider_id` held Telegram's **Bot API user id**
and did two jobs at once: the value matched on at login, and the `chat_id` the
notifier sends to. Those are different numbers — Telegram's own sample token
pairs `id: 987654321` with `sub: "1234123412341234123"` — and only one of them is
an identity:

- `sub` is in the discovery document's `claims_supported`; `id` is not.
- `subject_types_supported: ["public"]`, so `sub` is stable and identical across
  clients.
- `sub` needs only the `openid` scope. `id` needs `profile`, which Telegram drops
  outright when the bot is switched to EdDSA or ES256K signing in BotFather.
- Holding `id` does not even grant the right to message the user; that is the
  separate `telegram:bot_access` scope.

A second provider (VK) is planned, which makes both problems worse and adds a
third: RFC 9700 §4.4.2 requires a client talking to more than one authorization
server to defend against mix-up attacks.

## Decision

**We will merge login and linking into one callback per provider, carry the
intent in the OAuth state, and key identity on the OIDC subject.**

- One callback, `GET /auth/oauth/{provider}/callback`. The flow is chosen by an
  `intent` (`login` | `link`) in Authlib's state payload — server-side, bound to
  the signed session cookie, cleared on use. It is never read from a query
  param, and never inferred from whether a session cookie is present.
- A `link` state also records `initiator_user_id`. The callback refuses the link
  if the session is missing or belongs to a different user (`LinkInitiatorMismatch`
  → the `session_changed` toast). It **never** falls back to logging the user in.
- The `{provider}` segment stays in the URL. Each provider gets its own callback
  URI, per RFC 9700 §4.4.2.2.
- The state carries the `issuer` it was sent to (§4.4.2), compared back before
  the token exchange (§4.4.2.1).
- `social_identities` splits the two provider values: `subject` (renamed from
  `provider_id`) is the provider's stable account identifier and the only value
  matched on; `provider_user_id` is a nullable `BIGINT` holding the native
  account id, used only to address outbound messages. `UNIQUE (provider, subject)`
  is the `(iss, sub)` pair OIDC asks a relying party to key on, with the
  `SocialProvider` enum standing in for `iss`.

## Consequences

- The intent is now a real boundary — single-use, session-bound, tamper-proof
  without signing anything (RFC 9700 §4.7.1 is satisfied by construction, since
  the intent never rides in the `state` value).
- One redirect URI to register in BotFather instead of two. Adding VK is an enum
  member, an Authlib client, one more registered URI, and a CHECK-constraint
  migration — no new route.
- **The `{provider}` segment must not be folded into the state.** Doing so would
  remove the only mix-up defence available: Telegram does not advertise
  `authorization_response_iss_parameter_supported`, so RFC 9207's preferred `iss`
  response parameter cannot be used. If VK does advertise it, prefer it there.
- A login with an `openid`-only token now succeeds (degraded) instead of failing:
  `sub` identifies the user, `provider_user_id` stays `NULL`, and Telegram
  notifications are unavailable until a later login carries the `id`. The
  notifier treats a missing address as `UserNotReachable`, and `AuthorizeTelegram`
  backfills the column on login — which is why `social_identities` gained
  `updated_at` and left the append-only list in [backend.md](../backend.md).
- The migration **deletes every existing row**: `sub` cannot be derived from a
  Bot API id offline. This was acceptable only because the app is pre-production.
  Repeating this shape against real data would need a lazy backfill instead
  (match on subject, fall back to the legacy id, write the subject back).
- Still Telegram-shaped and deliberately left so until VK lands: the domain
  exceptions and their Russian copy name Telegram, and the unlink rule ("you
  still need an email") will have to become "you may not remove your last way to
  sign in".

## Alternatives considered

- **Keep two callbacks.** Rejected: the split was mistaken for a security
  property and is not one (see Context). It also costs a second registered
  redirect URI per provider for nothing.
- **One callback for all providers, provider in the state.** Rejected: directly
  contradicts RFC 9700 §4.4.2.2, and the `iss` alternative is unavailable here.
- **Infer the intent from the session cookie.** Rejected: a signed-in user
  clicking "log in with Telegram" would silently link instead, and a signed-out
  user finishing a link would be logged in as the account's owner.
- **Keep keying on the Bot API `id`.** Rejected: it is absent from
  `claims_supported`, and a bot switched to EdDSA/ES256K signing loses the
  `profile` scope that carries it — breaking login rather than just notifications.
- **A per-provider column (`telegram_user_id`, later `vk_user_id`).** Rejected:
  on a table that already carries a `provider` discriminator, every row would be
  all-NULL but one and each provider would cost a migration.
