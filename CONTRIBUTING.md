# Contributing

Thanks for helping with the FAN FAN companion app. This is the short version
for humans; the canonical, detailed rules live in [`AGENTS.md`](AGENTS.md) and
the guides under [`docs/`](docs/). **Where this file and `AGENTS.md` disagree,
`AGENTS.md` wins** — it's the source of truth, and this page only points at it.

## Getting started

Follow the [README quickstart](README.md#getting-started) to install the tools and
start the full stack in Docker. To install the optional Git hooks, run
`just backend-setup-hooks`.

For runtime Svelte inspection in the browser or through MCP, see
[Svelte DevTools](.agents/context/agent-tooling.md#svelte-runtime-diagnostics).

### Run app processes on the host

After `just setup`, start the backing services in Docker and apply migrations.

```sh
just run-infra
just backend-migrate
```

Run each app process in its own terminal.

```sh
just backend-dev
just backend-worker
just frontend-dev
```

The worker handles notifications and background jobs. Run `just backend-seed-demo`
to load sample data and `just stop-infra` to stop the backing services while keeping
that data. Host processes read the root `.env`, with `DB__HOST` and `NATS__HOST`
set to `localhost`.

### Local configuration

`just bootstrap` prepares `.env` from [`.env.example`](.env.example) when missing
and preserves existing configured values. With no SMTP configured, email login
codes appear in the API logs. Run this to read the logs from another terminal.

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --profile core logs api
```

Fresh configuration sets `WEB__ENABLED_OAUTH_PROVIDERS=[]`. Use the same setting
if an older `.env` shows an unconfigured social login button. Enable providers
only after supplying real credentials.

If the default ports are taken, set `FRONTEND_PORT` or `API_PORT` in `.env`.
When changing the frontend port, update `WEB__PUBLIC_URL` and `PUBLIC_SITE_URL`
to match. See the [deployment guide](docs/deployment.md) for production
configuration and the [backend guide](docs/backend.md#anti-corruption-layers-vendor-sync)
for external data sync.

## Finding and maintaining commands

Run `just` to list commands by group, or `just --group checks --list` to show
only checks. Existing names such as `run-dev` and `backend-lint` remain aliases.

Keep recipes in the root `justfile`. Use native [aliases](https://just.systems/man/en/aliases.html)
for alternate names and [dependencies](https://just.systems/man/en/dependencies.html)
for ordered steps, so checks share one invocation. Use `quote()` for text arguments
passed to the shell. Format changes with `just --fmt` and verify with
`just --fmt --check` (using the version pinned in `mise.toml`). CI runs this check
when the task file or tool pins change.

Routine Python commands and hooks use `uv run --locked`: update `uv.lock`
explicitly when changing dependencies. `just dev --build` rebuilds development
images; `just run-prod --no-build` skips rebuilding production images.

## Before you push

Run the check for what you touched. These commands do not fix source files:

- **Backend** — `just backend-check` (format, lint, types and import boundaries)
- **Frontend** — `just frontend-check` (format, lint and types)
- **Dockerfile** — `just dockerfile-lint`
- **Markdown or YAML outside `frontend/`** — `just root-lint`

To fix formatting, use `just backend-format`, `just frontend-format` or
`just root-format`. `just backend-fix` also applies Ruff fixes and sorts dependencies.
For types alone, use `just backend-typecheck` or `just frontend-typecheck`.
`just backend-lint` remains a check-only alias for the full backend gate.

Run the tests relevant to your change (`just backend-test`, `just frontend-test`,
or `just frontend-e2e`). See [`docs/testing.md`](docs/testing.md) for when to add tests.

## Language

User-facing copy is **Russian**; code, comments, docs, and issues/PRs are
**English**. See the language rule in [`AGENTS.md`](AGENTS.md).

## Commits & pull requests

- We **squash-merge**, so the **PR title** _is_ the commit that lands on `main`.
  It's linted as Conventional Commits — `type(scope): subject` with a lowercase
  subject — by CI. Allowed types and scopes are in [`AGENTS.md`](AGENTS.md)
  ("Commit & PR titles").
- Open the PR against `main`, fill in the
  [PR template](.github/pull_request_template.md), and link the issue with
  `Closes #123`.
- Deferring something? Leave a self-explaining `TODO`, or open an issue if it's
  cross-cutting or needs design — the promotion rule is in `AGENTS.md`.

## Reporting bugs & requesting features

Use the [issue forms](.github/ISSUE_TEMPLATE/). Please **don't** file security
problems as public issues — follow [`SECURITY.md`](SECURITY.md) instead.
