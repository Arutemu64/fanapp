# ADR-0037: Self-hosted ALTCHA over Yandex SmartCaptcha

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Project maintainers

## Context

The unauthenticated `request-login-code` endpoint creates an account for any
address and sends it a real email. Without protection, one script can spray codes
at thousands of addresses. The spam complaints that follow burn the sender
domain's reputation or get the SMTP account suspended, so real attendees stop
receiving codes, most likely in the festival month, when traffic and attention
peak.

[ADR-0009](0009-yandex-smartcaptcha-over-cloudflare-turnstile.md) guarded the
endpoint with Yandex SmartCaptcha. That kept the widget reachable from Russian
networks, but it still loaded a third-party script into the login page, needed a
Yandex Cloud account with billing, showed Yandex's data-processing notice, and
baked a client key into the frontend image at build time. The only limit behind
the captcha was a per-email cooldown, which does nothing against one source
writing to many addresses.

The app runs about a month before and a month after the festival. Its threat is
drive-by scripts, not a campaign targeting a fan convention.

## Decision

We will replace SmartCaptcha with **self-hosted
[ALTCHA](https://altcha.org/) proof-of-work** and add a **per-IP rate limit** on
`request-login-code`. Both run inside the existing API; no new container.

- **Challenge:** `GET /auth/captcha-challenge` returns a PoW v2 challenge from the
  `altcha` Python library (PBKDF2/SHA-256, cost 5000, 10-minute expiry),
  HMAC-signed with a key derived from `ALTCHA__HMAC_KEY`. It returns
  `{ challenge: null }` when the key is unset, which disables the captcha.
  Challenges use **deterministic mode**, which ALTCHA recommends for login
  protection ([ALTCHA: proof of work](https://altcha.org/docs/integration/proof-of-work-captcha/)):
  the server picks a random counter in 500–1000 and pre-solves it, so every
  client does exactly that much work, and a second derived key signs the
  solution so verification is a single HMAC. ALTCHA suggests counters of
  5000–10000; we stay 10× lower so a phone at the venue still finishes in a
  second or two. Pre-solving costs the server one derivation (~1 ms) per
  challenge, which the endpoint's per-IP limit below bounds.
- **Verification:** `AltchaCaptchaVerifier` (`adapters/captcha/altcha.py`) checks
  the solution locally. The library proves a solution is valid but cannot tell a
  replay, so the adapter records each spent challenge signature in Redis with
  `SET NX`, expiring with the challenge, and rejects a second use
  ([ALTCHA: replay attacks](https://altcha.org/docs/v2/cloud/integrate)).
- **Client:** the frontend solves headlessly with `solveChallengeWorkers` from
  the `altcha` npm package (`altcha/lib`) and its PBKDF2 Web Worker, with no
  widget UI. The email form starts solving on mount, so the token is usually
  ready by submit. Whether captcha is on comes from the API at runtime, so the
  frontend has no captcha env var.
- **Per-IP limit:** `RequestLoginCode` counts 20 requests per IP per 10 minutes on
  the existing `RateLimiter` port, before the captcha check, so a flood never
  reaches the PBKDF2 verification. The client IP comes from `X-Forwarded-For`,
  which Caddy overwrites for untrusted clients
  ([Caddy: reverse_proxy defaults](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)).
  The cap is generous because venue Wi-Fi and carrier-grade NAT share one
  address among many attendees. The challenge endpoint gets its own looser
  per-IP cap (60 per 10 minutes), following ALTCHA's advice to rate-limit
  challenge generation as well as verification
  ([ALTCHA: security recommendations](https://altcha.org/docs/integration/security-recommendations/)),
  and `captcha_token` is capped at 4 KB: real payloads are well under that, and
  ALTCHA's advisories show parsers are where hostile payloads strike first
  ([ALTCHA: security advisory](https://altcha.org/legal/security-advisory/)).

## Consequences

- No third-party script, account, billing or data-processing notice on the login
  path. Turning the captcha on or off is a backend `.env` change, not an image
  rebuild.
- Proof-of-work raises the cost per request; it does not detect bots. An attacker
  willing to burn CPU can still solve challenges, and the per-IP limit is what
  caps one source. If abuse appears, raise `CHALLENGE_COUNTER_MIN`/`_MAX` or
  `CHALLENGE_COST`, or lower the IP cap.
- Difficulty is a trade-off against slow phones at the venue. The cost follows
  ALTCHA's suggestion; the counter is deliberately below it. A counter of 750
  took 0.66 s single-threaded on a 4-core server and the client splits it across
  workers, but the solve time on a phone is an estimate, not a measurement on
  venue hardware.
- Each login-code request now costs one Redis write for the replay guard and one
  for the IP counter.
- Deploying requires setting `ALTCHA__HMAC_KEY` on the server; without it the
  captcha is off. `SMARTCAPTCHA__SERVER_KEY` and `PUBLIC_SMARTCAPTCHA_CLIENT_KEY`
  are gone.

## Alternatives considered

- **Keep SmartCaptcha** — rejected for the reasons above; it also left
  multi-address spraying unlimited.
- **Drop the captcha, keep only rate limits** — rejected: a distributed sender
  slips under a per-IP cap, and a global email cap as the backstop would lock
  real users out in exactly that case.
- **ALTCHA's widget (`<altcha-widget display="invisible">`)** — rejected: about
  twice the minified size of the solver library (119 KB vs 62 KB, before
  tree-shaking) for UI we never show, and it creates its
  workers from `blob:` URLs, which a future CSP would have to allow.
- **ALTCHA Sentinel (self-hosted server)** — rejected: a separate service for
  features we don't need (code challenges, classification) at our scale.
