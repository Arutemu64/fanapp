# fanapp

Monorepo with:
- `frontend/`: SvelteKit app (pnpm).
- `backend/`: Python app (uv, Alembic, Ruff).
- `docker-compose.yml`: local infrastructure and app services.

## Project layout

```text
.
├── frontend/            # SvelteKit UI
├── backend/             # Python backend (API, bot, workers)
├── docker-compose.yml   # Local services (db, redis, nats, web, bot, ...)
└── justfile             # Common backend/dev commands
```

## Minimal local prerequisites

Install these before first run:

```bash
# Frontend
node --version
pnpm --version

# Backend
python --version
uv --version

# Infrastructure
docker --version
docker compose version
```

## First-run sequence

### 1) Backend (deps + env + migrations)

From repo root:

```bash
cd backend
uv sync --all-groups
```

Create/set backend env file (example path; keep secrets local):

```bash
# Create/update repo-root env file used by docker-compose
cd /workspace/fanapp
$EDITOR .env

# Point backend to that same env file when running locally
export ENV_FILE=/workspace/fanapp/.env
```

Run database migrations / bootstrap:

```bash
cd /workspace/fanapp/backend
uv run alembic upgrade head
uv run python -m fanfan.main.migration
```

### 2) Frontend (deps + dev server)

```bash
cd /workspace/fanapp/frontend
pnpm install
pnpm dev
```

## Run only needed services (example: web + db + redis)

Start only the services needed for API work:

```bash
cd /workspace/fanapp
docker compose --profile web up -d db redis migration web
```

Follow logs:

```bash
docker compose logs -f web db redis migration
```

Stop them:

```bash
docker compose stop web db redis migration
```

## Common checks

### Frontend

```bash
cd /workspace/fanapp/frontend
pnpm check
pnpm lint
```

### Backend (from `justfile`)

```bash
cd /workspace/fanapp
just lint
just migrate
# create migration
just generate "add_new_table"
```

## For Codex agents

- API schema generation is in the frontend script:

```bash
cd /workspace/fanapp/frontend
pnpm generate-api
```

- Environment variables are expected in:
  - `/workspace/fanapp/.env` for `docker-compose.yml` services.
  - Path referenced by `ENV_FILE` for backend local runs.
  - Frontend runtime env via SvelteKit public/private env variables (`PUBLIC_API_URL`, `PRIVATE_API_URL`).

- Avoid scanning heavy/generated dependency paths unless strictly needed:

```text
frontend/node_modules
frontend/.svelte-kit
backend/.venv
```
