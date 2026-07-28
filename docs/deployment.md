# Deployment

The server runs the **prebuilt** GHCR images instead of building from source —
see [`docker-compose.prod.yml`](../docker-compose.prod.yml). Only the
application *build* moves to CI; the runtime config stays on the host. To test
the exact same images locally first, build them from your working tree with
`just run-prod` (no registry needed).

## Reusing this for another event

The published GHCR images are built for the FAN FAN deployment. They are fine to
pull for a look, but they are not a base to run your own event on — fork the
repository and publish images from your fork instead.

Two things make them deployment-specific. The frontend is a static SPA, so its
`PUBLIC_*` values are inlined into the bundle at build time (see
[frontend.md](frontend.md)) from this repository's Actions variables:
`PUBLIC_VAPID_KEY` must match the private VAPID PEM held by *our* backend,
`PUBLIC_SMARTCAPTCHA_CLIENT_KEY` is a Yandex sitekey bound to our account and
domains, and `PUBLIC_SENTRY_DSN` points at our error-reporting project. And both
images ship the festival branding, which the [README's license
section](../README.md#license) excludes from the MIT grant.

From a fork, four things need to change:

1. **Branding.** Replace the four excluded asset paths listed in the README, and
   the name, description and `theme_color` in
   [`frontend/static/manifest.json`](../frontend/static/manifest.json).
2. **Actions variables.** Set your own `PUBLIC_VAPID_KEY` (the public half of the
   keypair `just bootstrap` generates into `secrets/`), plus
   `PUBLIC_SMARTCAPTCHA_CLIENT_KEY` and the `PUBLIC_SENTRY_*` values if you use
   those integrations. Leave a variable unset to disable its feature.
3. **A build.** A variable change alone does not trigger a publish — run
   [`docker-publish.yml`](../.github/workflows/docker-publish.yml) manually from
   the Actions tab afterwards, or push to `main`.
4. **Image names.** The `image:` lines in
   [`docker-compose.prod.yml`](../docker-compose.prod.yml) name
   `ghcr.io/arutemu64/…`; point them at your fork's packages.

`PUBLIC_API_URL` is deliberately not on that list — it defaults to the relative
`/api`, which is what keeps the bundle domain-agnostic (see [Reverse proxy
(Caddy)](#reverse-proxy-caddy-https-and-http-testing) below).

Everything else — database, Telegram bot, SMTP, TicketsCloud, Cosplay2 — is
runtime config in `.env` and needs no rebuild.

## What the server needs on disk

Cloning the repo is the simplest way to get all of it:

| Path | Why |
| --- | --- |
| `docker-compose.yml` + `docker-compose.prod.yml` | Service definitions; `just deploy` passes both. |
| `.env` | All runtime config. Start from `.env.example`. |
| `config/` | Redis config, mounted read-only. |
| `secrets/` | VAPID PEM keys, mounted read-only. Ships empty — the keys are yours. |
| `backend/alembic.ini` | Read by the `migration` service. |

## One-time setup

```sh
docker login ghcr.io          # use a read-only PAT / deploy token, not a password
cp .env.example .env          # fill in placeholders (see the README's Getting started)
# Put the VAPID keys in secrets/ and make them readable by the container user
# (backend runs as uid 999):
chmod 600 secrets/private_key.pem
sudo chown 999:999 secrets/*.pem
```

Generate the VAPID keys with `just bootstrap` (or `just backend-generate-vapid`)
on any machine and copy the PEMs across; `PUBLIC_VAPID_KEY` in `.env` must match
the public PEM.

### Telegram login: register the URLs with BotFather

Telegram login needs one step that is not in `.env`. In [@BotFather](https://t.me/BotFather),
open **Bot Settings → Web Login** and register, for your domain:

| Kind | Value |
| --- | --- |
| Origin | `https://example.com` |
| Redirect URI (login) | `https://example.com/api/auth/auth/telegram` |
| Redirect URI (account linking) | `https://example.com/api/me/connections/telegram/callback` |

The same screen shows the Client ID and Client Secret that `BOT__CLIENT_ID` and
`BOT__CLIENT_SECRET` want. Telegram only processes logins and redirects for
pre-registered URLs, so a bot with correct credentials but unregistered URLs
fails on Telegram's own authorization page and leaves nothing in the app logs to
explain it.

The `/api` prefix is Caddy's (`handle_path /api*`), which the backend mirrors via
uvicorn's `root_path` — that is why the callback URLs the app generates carry it.
The doubled `auth/auth` is not a typo: the login router is mounted under `/auth`
and declares the callback at `/auth/telegram`. Changing it would invalidate a URL
already registered in BotFather, so it stays.

## Deploying

```sh
just deploy                   # docker compose ... -f docker-compose.prod.yml pull && up -d
```

This pulls the images and restarts, building nothing on the host. Migrations run
automatically via the `migration` service before the API starts.

### Pinning a build, and rolling back

By default `just deploy` tracks the latest `main` build (the `latest` tag). Pin a
specific build — which is also how you roll back — by setting `IMAGE_TAG` in
`.env`, then deploying again:

```sh
IMAGE_TAG=sha-1a2b3c4
```

Every push to `main` publishes a `sha-<short-sha>` tag, and every `v*` tag
publishes that release, so any past build is reachable by tag.

## Reverse proxy (Caddy): HTTPS and HTTP testing

The app is meant to run behind a reverse proxy that puts the frontend and the API
on **one origin**: [`Caddyfile.example`](../Caddyfile.example) routes `/api*` to
the backend and everything else to the SvelteKit frontend. Because the API is
same-origin, the browser never makes a cross-origin request, so **no CORS config
is needed**.

The frontend is a static SPA (`adapter-static`, no SSR) served by NGINX, and it
calls the API with a **relative base** (`PUBLIC_API_URL=/api`, the default),
which resolves against whatever origin serves the app. That keeps the bundle
domain-agnostic — the same build (and the prebuilt GHCR image) works on any
domain with no rebuild (see [frontend.md](frontend.md)).

`just run-prod` exposes the apps on `127.0.0.1:3000` (frontend) and
`127.0.0.1:8000` (API); run Caddy with `Caddyfile.example` in front to reach them
on a single origin (e.g. `http://localhost`).

With the relative default you only set the origin-dependent values to match how
the browser reaches the site:

| `.env` / Caddy | HTTPS (production) | HTTP (local / insecure testing) |
|---|---|---|
| Caddy site block | your domain, e.g. `example.com { … }` (auto-TLS) | `:80 { … }` (as shipped) |
| `WEB__PUBLIC_URL` | `https://example.com/` | `http://localhost/` |
| `PUBLIC_API_URL` | `/api` (relative — domain-agnostic) | `/api` |
| `WEB__COOKIE_SECURE` | `True` | `False` |
| `WEB__CORS_ALLOW_ORIGINS` | unset (same-origin) | unset (same-origin) |

`WEB__COOKIE_SECURE=False` is **required** over plain HTTP — a `Secure` cookie is
never sent over HTTP, which would otherwise break login (including the Telegram
OAuth callback, whose state cookie follows the same flag). When you switch a host
between HTTP and HTTPS, clear its cookies first, or stale `Secure` cookies look
like an auth bug.

### Split-origin (optional)

To serve the API on a *different* origin than the site, set `PUBLIC_API_URL` to
that absolute URL (e.g. `https://api.example.com`) — this requires a rebuild,
since `PUBLIC_API_URL` is baked into the bundle at build time — and set
`WEB__CORS_ALLOW_ORIGINS` to the public app origin exactly (scheme + host, no
trailing slash, no path).
