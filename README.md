# fanapp

Monorepo with two independent apps (no workspaces):

- `frontend/` — SvelteKit + pnpm
- `backend/` — FastAPI + uv

`justfile` at repo root is the unified command entrypoint.

## No-workspace model

This repository intentionally **does not use npm/pnpm/yarn workspaces**.

- Frontend dependencies stay in `frontend/node_modules`
- Backend dependencies stay in `backend/.venv`
- Root is used only for orchestration (`justfile`, `docker-compose.yml`, docs/config)

## Prerequisites

```bash
node --version
pnpm --version
python --version
uv --version
docker --version
docker compose version
just --version
```

## Quick start

From repo root:

```bash
just install
```

Run apps in separate terminals:

```bash
just backend-dev
just frontend-dev
```

## Useful commands

### Frontend

```bash
just frontend-install
just frontend-dev
just frontend-check
just frontend-lint
just frontend-build
just frontend-generate-api
```

### Backend

```bash
just backend-install
just backend-dev
just backend-lint
just backend-migrate
just backend-generate add_new_table
```

### Combined

```bash
just install
just lint
just check
just dev
```

## Docker infra helpers

```bash
just infra-up-web
just infra-logs-web
just infra-stop-web
```

## Environment strategy

Recommended split:

- `/.env` — only Docker Compose variables (shared service wiring)
- `backend/.env` (or `ENV_FILE`) — backend runtime values/secrets
- `frontend/.env.local` — frontend runtime values

This keeps local app secrets close to each app while allowing compose orchestration from root.
