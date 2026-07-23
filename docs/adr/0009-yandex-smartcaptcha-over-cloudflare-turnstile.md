# ADR-0009: Yandex SmartCaptcha over Cloudflare Turnstile

- **Status:** Accepted
- **Date:** 2026-07-23
- **Deciders:** Project maintainers

## Context

The unauthenticated `request-login-code` flow is guarded by a captcha to keep
bots from burning the email/rate-limit budget. It was originally wired to
Cloudflare Turnstile: a frontend widget loaded from `challenges.cloudflare.com`
plus server-side `siteverify`.

The app's entire audience is attendees of a Russian anime convention. Cloudflare
is frequently throttled or degraded for Russian networks (TSPU/Roskomnadzor
filtering). The backend verification fails open on an outage, so a blocked
`siteverify` does not lock anyone out — but the **widget script** is the real
exposure: if `challenges.cloudflare.com` fails to load in the browser, the user
never obtains a token, the frontend captcha gate times out, and login silently
breaks for exactly the users we care about.

The captcha already sits behind the `CaptchaVerifier` port
(`application/ports/captcha.py`), so the provider is swappable without touching
the domain or the login interactor.

## Decision

We will use **Yandex SmartCaptcha** instead of Cloudflare Turnstile. Yandex
hosts the widget and validation endpoint inside Russia
(`smartcaptcha.cloud.yandex.ru`), so it stays reachable for our audience.

Concretely:

- Backend adapter `adapters/captcha/yandex.py` (`SmartCaptchaVerifier`) POSTs to
  `https://smartcaptcha.cloud.yandex.ru/validate` and accepts only
  `status: "ok"`; it keeps the same fail-open-on-transport-error / 5xx behaviour.
- Config is `SmartCaptchaConfig.server_key` (`SMARTCAPTCHA__SERVER_KEY`); the
  frontend client key is `PUBLIC_SMARTCAPTCHA_CLIENT_KEY`. Both unset = captcha
  disabled (`NoOpCaptchaVerifier`), unchanged from before.
- The frontend loads the widget in **invisible mode**; because invisible mode
  mints a token only after `execute()`, `CaptchaWidget.svelte` exposes an
  `execute` binding the forms trigger on submit.
- The request DTO field is the provider-neutral `captcha_token` (was
  `turnstile_token`).

## Consequences

- The captcha dependency in the login path is reachable for the target audience;
  we remove a foreign single point of failure.
- Operating SmartCaptcha requires a **Yandex Cloud account with billing**, a
  heavier onboarding than Turnstile's standalone free key. Usage cost is
  negligible at our volume.
- Yandex shows a **data-processing "shield" notice** by default. We keep it
  visible; hiding it obliges us to notify users about data processing ourselves,
  which we chose not to take on.
- The `CaptchaVerifier` port and the fail-open contract are unchanged, so a
  future provider swap remains a single-adapter change.

## Alternatives considered

- **Keep Cloudflare Turnstile** — rejected: the widget CDN is the exact thing
  that is unreliable for Russian users, and no server-side setting fixes a script
  that never loads in the browser.
- **Support both providers behind the port, selected by config** — rejected as
  premature: it doubles the frontend widget code and docs for a fallback we have
  no concrete need for. The port keeps a later re-introduction cheap if that
  changes.
