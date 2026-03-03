# fanapp

## MCP configuration

This repository includes a repo-level MCP configuration at `.mcp.json` with a `svelte` server entry.

### What the Svelte MCP server provides

The Svelte MCP server (`@sveltejs/mcp`) exposes Svelte and SvelteKit-aware context/tools to MCP-compatible clients so they can better understand project files, framework conventions, and related development workflows.

### Startup and log verification

From the repository root, you can verify the server starts by running:

```sh
npx -y @sveltejs/mcp
```

When startup is successful, you should see normal MCP server startup logs (for example, initialization/ready output) and no module resolution errors. The configured working directory is `frontend`, so context resolution happens against this app.

### Expected runtime availability

Running this MCP server expects:

- Node.js available on `PATH` (to run `npx`)
- `pnpm` typically available for this repository's frontend workflow (`frontend/pnpm-lock.yaml`), although MCP startup itself is invoked via `npx`
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


## VS Code monorepo workflow

Use the committed workspace file to get correct frontend/backend context, tasks, and extension recommendations:

```bash
code fanapp.code-workspace
```

This workspace config provides:
- Visible repo root for shared files (`README.md`, `docker-compose.yml`, `justfile`) plus separate `frontend`/`backend` roots for tooling context.
- Shared excludes for heavy/generated directories.
- Frontend defaults (`eslint.workingDirectories`, TypeScript SDK path).
- Backend defaults (Python interpreter path and `src` import resolution).
- Task shortcuts for common frontend/backend commands.

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
