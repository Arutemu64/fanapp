# ADR-0013: Provider-agnostic social identity flows, and a last-sign-in-method unlink rule

- **Status:** Accepted
- **Date:** 2026-08-05
- **Deciders:** Backend + frontend

## Context

[ADR-0012](0012-single-oauth-callback-keyed-on-the-oidc-subject.md) merged login
and linking into one callback per provider and keyed identity on the OIDC
subject, but left the code **"Telegram-shaped … until VK lands"**: the interactors
(`AuthorizeTelegram`/`AuthorizeVk`, `LinkTelegramAccount`/`LinkVkAccount`,
`UnlinkTelegramAccount`/`UnlinkVkAccount`) and their exceptions were per-provider
copies differing only by a `SocialProvider` constant. VK has landed, so the
duplication is now live and every future provider would multiply it.

ADR-0012 also flagged a rule that only breaks with a second provider: unlinking
required the user to have an email. With one provider that was a fine proxy for
"keep a way in". With two it is wrong — a user holding both Telegram and VK but
no email was blocked from unlinking *either*, even though removing one still
leaves the other as a way to sign in. Password and email-code login both key off
the email address (`AuthenticateUser.get_by_email`), so email is the single
non-social sign-in method; a linked provider is the other.

## Decision

**We will collapse the per-provider social flows into one provider-parameterized
interactor each, and refuse an unlink only when it would remove the user's last
remaining sign-in method.**

- `AuthorizeSocialLogin`, `LinkSocialAccount`, `UnlinkSocialAccount` each take the
  `provider` in their input DTO. The six provider-specific interactors are gone.
- Exceptions become provider-agnostic: `SocialAccountLinkedToAnotherUser`,
  `UserAlreadyHasProviderLinked`, and `CannotRemoveLastSignInMethod` replace the
  six Telegram/VK-named ones. The OAuth callback already funnelled the link
  exceptions into shared, provider-neutral toast codes, so no user-facing copy
  changes for those.
- `UnlinkSocialAccount` refuses the removal (`CannotRemoveLastSignInMethod`) only
  when the user has no email **and** `SocialIdentityGateway.count_by_user` shows
  this is their last identity — otherwise email or the other provider keeps them
  reachable.
- The `{provider}` URL segment and the per-provider callback/redirect URIs stay
  exactly as ADR-0012 set them; this ADR changes only the layers behind the
  routes. The two unlink endpoints (`/me/connections/{telegram,vk}`) remain as
  thin delegators to the one interactor, preserving the frontend's typed client.

## Consequences

- Adding a provider is now what the `SocialProvider` docstring already claims: an
  enum member, an Authlib client, a callback URI, and a CHECK-constraint
  migration — **no new interactor, exception, or route.**
- A latent bug is fixed: the gateway's integrity-error translation raised the
  Telegram-named exception for a VK unique-constraint race. It now maps to the
  provider-agnostic exceptions.
- The unlink rule is now correct for N providers and states its own intent. It is
  a genuine behaviour change from ADR-0012's "email required", not a rename.
- `count_by_user` is a plain (unlocked) count. Two concurrent unlinks of
  *different* providers by an email-less user could each see count > 1 and both
  delete, leaving zero. The window needs two simultaneous requests for one
  account and the UI gates unlinks one at a time behind a confirm tap, so the
  risk is accepted rather than serialized (which would invite a deadlock between
  the two row locks).

## Alternatives considered

- **Keep per-provider interactors/exceptions.** Rejected: pure duplication that
  ADR-0012 only tolerated as a temporary shape, and the source of the VK
  integrity-error bug.
- **One DELETE `/me/connections/{provider}`.** Rejected for now: it would churn
  the frontend's typed client paths for no behavioural gain; the two thin
  endpoints already share the one interactor.
- **Keep "email required to unlink".** Rejected: it locks a two-provider,
  no-email user out of unlinking either account — the exact gap ADR-0012 named.
