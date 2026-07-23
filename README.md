# FAN FAN

Helper web app for the **FAN FAN** Russian anime convention. It gives attendees the event schedule, voting, notifications, and ticket-linked profiles from their phone, and gives organizers the tools to run all of it. Audience is teen to young-adult and non-technical, so the UI is mobile-first and all user-facing copy is in Russian.

This is a monorepo: a FastAPI backend, a SvelteKit frontend, and a shared OpenAPI contract between them.

## Features

- **Schedule** — public event schedule with live changes, per-user subscriptions, and organizer management/import tools.
- **Voting** — nominations and voting, with cosplay data synced from Cosplay2.
- **Notifications** — in-app feed plus Web Push (VAPID) for broadcasts and per-user alerts.
- **Auth** — sign in via Telegram, email code, one-time login code, or credentials; cookie-based sessions.
- **Profiles & tickets** — user profile, linked tickets (synced from TicketsCloud), account connections, and security settings.
- **Feedback** — user feedback submission.
- **Telegram bot** — companion bot sharing the same backend and domain logic.
- **Live updates** — Server-Sent Events (SSE) push real-time changes to the client.

## Stack

| Layer | Tech |
|---|---|
| Frontend | SvelteKit (Svelte 5 runes), Flowbite-Svelte, Tailwind CSS v4, `pnpm` |
| Backend | FastAPI, SQLAlchemy + Alembic, Dishka (DI), `uv` |
| Data / infra | PostgreSQL, Redis (Valkey), NATS + FastStream |
| Jobs | APScheduler (periodic syncs), FastStream consumers (domain events) |
| Tooling | Docker Compose, `just` task runner |

The backend follows clean / hexagonal architecture — pure `core` and `application` layers, infrastructure behind ports in `adapters`. See [`AGENTS.md`](AGENTS.md) and [`docs/`](docs/) for the full guidelines.

## Repository layout

```text
backend/    FastAPI app (core / application / adapters / presentation / main)
frontend/   SvelteKit app (routes + lib: components, api, services, utils)
shared/     Shared OpenAPI spec
config/     Redis config, VAPID keys, infra config
docs/       Architecture guides (backend.md, frontend.md, api.md)
```

## Requirements

- Python ≥ 3.14 and [`uv`](https://docs.astral.sh/uv/)
- Node.js + [`pnpm`](https://pnpm.io/)
- [`just`](https://github.com/casey/just)
- Docker + Docker Compose (for the full environment)
- On **Windows**, run `just` from **Git Bash** or **WSL** (not cmd/PowerShell): the
  recipes are POSIX shell. Git Bash ships with
  [Git for Windows](https://git-scm.com/download/win). (`just bootstrap` itself is a
  pure-Python script — no bash/openssl needed — but the other recipes still expect a
  POSIX shell.)

> Optional: [`mise`](https://mise.jdx.dev) (or `asdf`) reads the pinned
> versions from [`mise.toml`](mise.toml) — run `mise install` to get the exact
> Python / Node / pnpm / uv / just this repo expects in one step. Docker is not
> managed by mise; install it separately.

## Getting started

### 1. Configure

```sh
just bootstrap
```

This creates `.env` from the template, fills the generated secrets (DB / Redis /
NATS passwords, `WEB__SECRET_KEY`), and generates the Web Push VAPID keys
(`secrets/private_key.pem`, `secrets/public_key.pem`, `PUBLIC_VAPID_KEY`). It is
idempotent — re-run anytime; it never overwrites values you've already set.

Both the web API and the bootstrap defaults are designed to boot with no real
third-party credentials, so you can start exploring immediately:

- `BOT__*` — the placeholder values are format-valid, so the web API starts with
  them. Telegram login and Telegram notifications stay disabled until you set a
  real bot (create one via [@BotFather](https://t.me/BotFather)); email and
  credentials login work without it. The bot *process* needs a real token to run.
- `MAIL__*` (SMTP) — optional; leave unset and outgoing emails are logged instead
  of sent (email login/confirmation codes appear in the app logs).
- `PUSH__SUBSCRIBER` — your contact email for Web Push.

The optional integration blocks stay commented out.

Local (non-Docker) frontend dev reads this same root `.env` — SvelteKit is configured to load it from the repo root (`kit.env.dir` / Vite `envDir`), so there is no separate `frontend/.env` to maintain.

### 2. Run with Docker (full environment)

```sh
just run-dev      # dev: hot-reload via Compose --watch
just run-prod     # prod: includes ops profile (pgbackup)
```

This brings up the frontend, API, FastStream consumer, scheduler, Postgres, Redis, and NATS. Migrations run automatically via the `migration` service.

- Frontend: http://localhost:3000
- API: http://localhost:8000

Both host ports are overridable if 3000/8000 are taken — set `FRONTEND_PORT` / `API_PORT` in `.env` (see `.env.example`). Update `Caddyfile.example` to match if you use it.

### 3. Run locally (without Docker)

Install dependencies, then start each side in its own terminal:

```sh
just backend-install
just frontend-install

just backend-migrate     # apply DB migrations (needs Postgres reachable)
just backend-dev         # FastAPI on :8000 (WEB__PORT)
just frontend-dev        # SvelteKit dev server on :3000 (FRONTEND_PORT)
```

## Common commands

All commands run from the repo root via `just`.

| Command | What it does |
|---|---|
| `just backend-dev` / `just frontend-dev` | Start backend / frontend locally |
| `just backend-migrate` | Apply Alembic migrations |
| `just backend-generate <name>` | Autogenerate a migration |
| `just backend-lint` | Format + lint + type-check backend |
| `just backend-typecheck` | Run `ty` type checker |
| `just frontend-lint` / `just frontend-check` | Lint / type-check frontend |
| `just frontend-generate-api` | Regenerate frontend API types from the OpenAPI spec |
| `just backend-sync tcloud` | Sync tickets from TicketsCloud |
| `just backend-sync cosplay2` | Sync cosplay data from Cosplay2 |

> The frontend talks to the backend through generated types in `frontend/src/lib/api/v1.d.ts`. Whenever backend endpoints or schemas change, run `just frontend-generate-api` to keep the contract in sync.

## Continuous integration

Every pull request and every push to `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml) on GitHub Actions. It mirrors the local quality gates:

- **Backend** — Ruff lint + format check, `ty` type check, and the full `pytest` suite. Integration tests spin up Postgres and Redis automatically via testcontainers (Docker is preinstalled on the runner).
- **Frontend** — Prettier + ESLint, `svelte-check`, and a production build.
- **Dockerfiles** — [hadolint](https://github.com/hadolint/hadolint) best-practice linting (config in [`.hadolint.yaml`](.hadolint.yaml)). Run locally with `just dockerfile-lint` (hadolint comes from `mise`) or via the pre-commit hook.

Each job runs only when its area changed (`dorny/paths-filter`), so unrelated edits skip the gates they don't affect.

CI is check-only: unlike `just backend-lint`, it never auto-fixes — a violation fails the run. Run the local `just` commands before pushing to get the same result faster.

[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) additionally builds the backend and frontend images and pushes them to the GitHub Container Registry (GHCR) on pushes to `main` (which move the `latest` tag) and on `v*` tags. The `SENTRY_AUTH_TOKEN` repository secret is passed only to the frontend build (source-map upload); it is consumed in a discarded build stage and never ends up in the published image.

## Deployment

The server runs the **prebuilt** GHCR images instead of building from source — see [`docker-compose.prod.yml`](docker-compose.prod.yml). To test the exact same images locally first, build them from your working tree with `just run-prod` (no registry needed).

One-time server setup:

```sh
docker login ghcr.io          # use a read-only PAT / deploy token, not a password
cp .env.example .env          # fill in placeholders (see Getting started)
# Put the VAPID keys in secrets/ (the dir ships empty in the repo) and make
# them readable by the container user (backend runs as uid 999):
chmod 600 secrets/private_key.pem
sudo chown 999:999 secrets/*.pem
```

Deploy (pulls the images and restarts, builds nothing on the host):

```sh
just deploy                   # docker compose ... -f docker-compose.prod.yml pull && up -d
```

By default `just deploy` tracks the latest `main` build. Pin a specific build (or roll back) by setting `IMAGE_TAG` in `.env`, e.g. `IMAGE_TAG=sha-1a2b3c4`. The server still needs the repo's compose files, `.env`, `config/` (Redis config + VAPID keys), and `backend/alembic.ini` on disk — only the application *build* moves to CI, not the runtime config.

### Reverse proxy (Caddy): HTTPS and HTTP testing

The app is meant to run behind a reverse proxy that puts the frontend and the API on **one origin**: [`Caddyfile.example`](Caddyfile.example) routes `/api*` to the backend and everything else to the SvelteKit frontend. Because the API is same-origin, the browser never makes a cross-origin request, so **no CORS config is needed**. The frontend is a static SPA (`adapter-static`, no SSR) served by NGINX, and it calls the API with a **relative base** (`PUBLIC_API_URL=/api`, the default), which resolves against whatever origin serves the app. That keeps the bundle domain-agnostic — the same build (and the prebuilt GHCR image) works on any domain with no rebuild (see [`docs/frontend.md`](docs/frontend.md)).

`just run-prod` exposes the apps on `127.0.0.1:3000` (frontend) and `127.0.0.1:8000` (API); run Caddy with `Caddyfile.example` in front to reach them on a single origin (e.g. `http://localhost`).

With the relative default you only set the origin-dependent values to match how the browser reaches the site:

| `.env` / Caddy | HTTPS (production) | HTTP (local / insecure testing) |
|---|---|---|
| Caddy site block | your domain, e.g. `example.com { … }` (auto-TLS) | `:80 { … }` (as shipped) |
| `WEB__BASE_URL` | `https://example.com/` | `http://localhost/` |
| `PUBLIC_API_URL` | `/api` (relative — domain-agnostic) | `/api` |
| `WEB__COOKIE_SECURE` | `True` | `False` |
| `WEB__CORS_ALLOW_ORIGINS` | unset (same-origin) | unset (same-origin) |

`WEB__COOKIE_SECURE=False` is **required** over plain HTTP — a `Secure` cookie is never sent over HTTP, which would otherwise break login (including the Telegram OAuth callback, whose state cookie follows the same flag). When you switch a host between HTTP and HTTPS, clear its cookies first, or stale `Secure` cookies look like an auth bug.

**Split-origin (optional):** to serve the API on a *different* origin than the site, set `PUBLIC_API_URL` to that absolute URL (e.g. `https://api.example.com`) — this requires a rebuild, since `PUBLIC_API_URL` is baked into the bundle at build time — and set `WEB__CORS_ALLOW_ORIGINS` to the public app origin exactly (scheme + host, no trailing slash, no path).

## External integrations

Optional, enabled via `.env`:

- **TicketsCloud** (`TCLOUD__*`) — ticket sync.
- **Cosplay2** (`COSPLAY2__*`) — cosplay / voting data sync.
- **Scheduler** (`SCHEDULER__SYNC_*_CRON`) — cron strings (in `TIMEZONE`) that run the syncs periodically. Unset = disabled. After editing, `docker compose restart scheduler`. Trigger a sync manually any time with `docker compose run --rm api cli sync tcloud`.

## Documentation

- [`AGENTS.md`](AGENTS.md) — monorepo guidelines and core constraints
- [`docs/backend.md`](docs/backend.md) — backend architecture (domain, ports, DI, events)
- [`docs/frontend.md`](docs/frontend.md) — SvelteKit SPA rules, styling, components
- [`docs/api.md`](docs/api.md) — type-safe API integration
