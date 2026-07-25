# =========================
# Monorepo helper commands
# =========================
# No workspaces: frontend and backend keep isolated dependency trees.

# ---- Setup ----
# One-command local setup: create .env from the template, fill generated
# secrets (DB/Redis/NATS passwords, WEB__SECRET_KEY), and generate VAPID keys.
# Idempotent — re-run anytime; it never overwrites values you've already set.
bootstrap:
    cd backend && uv run python scripts/bootstrap.py

# ---- Frontend (SvelteKit + pnpm) ----
frontend-install:
    cd frontend && pnpm install

frontend-dev:
    cd frontend && pnpm dev

frontend-check:
    cd frontend && pnpm check

frontend-lint:
    cd frontend && pnpm lint

frontend-build:
    cd frontend && pnpm build

frontend-generate-api: backend-generate-openapi
    cd frontend && pnpm generate-api

# ---- Backend (FastAPI + uv) ----
backend-install:
    cd backend && uv sync --all-groups

backend-setup-hooks:
    cd backend && uv run pre-commit install

backend-dev:
    cd backend && uv run python -m fanfan.main.web

backend-generate-openapi:
    cd backend && uv run python -m fanfan.main.generate_openapi

# Generate a VAPID keypair into secrets/ (overwrites existing keys)
backend-generate-vapid:
    cd backend && uv run generate-vapid

backend-format:
    cd backend && uv run ruff format src/fanfan tests scripts --respect-gitignore

backend-check:
    cd backend && uv run ruff check src/fanfan tests scripts --respect-gitignore --fix --unsafe-fixes

backend-test:
    cd backend && uv run pytest tests

backend-test-integration:
    cd backend && uv run pytest tests/integration

backend-sync TARGET:
    cd backend && uv run python -m fanfan.main.cli sync {{ TARGET }}

backend-typecheck:
    cd backend && uv run ty check src/fanfan

backend-import-lint:
    cd backend && uv run lint-imports

backend-lint: backend-format backend-check backend-typecheck backend-import-lint

backend-migrate:
    cd backend && uv run alembic upgrade head

backend-generate MIGRATION_NAME:
    cd backend && uv run alembic revision --autogenerate -m "{{ MIGRATION_NAME }}"

# Autogenerate a migration against a throwaway Postgres 18 (matches prod + CI).
# Needs Docker; use where no app database is running (e.g. Claude Code on the
# web). Always REVIEW the result — autogenerate misses renames. See script.
backend-generate-auto MIGRATION_NAME:
    cd backend && uv run python scripts/generate_migration.py "{{ MIGRATION_NAME }}"

# Fail if ORM models drift from migrations (spins a throwaway Postgres via testcontainers)
backend-check-migrations:
    cd backend && uv run pytest tests/integration/test_migrations.py

# ---- Dockerfiles (hadolint) ----
# Lint both Dockerfiles with hadolint (installed via mise; reads .hadolint.yaml
# from the repo root). Same check as the pre-commit hadolint hook and the CI
# hadolint job.
dockerfile-lint:
    hadolint backend/Dockerfile frontend/Dockerfile

# ---- Docker infra helpers ----
# Dev: Compose auto-builds any image that doesn't exist yet, and `--watch`
# live-syncs source + rebuilds only when package.json/pnpm-lock/uv.lock change —
# so no forced rebuild is needed per start (that just slows startup). Pass
# build="--build" to force a rebuild (e.g. after editing a Dockerfile).
run-dev build="":
    docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile core up {{build}} --watch

# Pass build="" to skip image rebuild (default rebuilds)
run-prod build="--build":
    docker compose -f docker-compose.yml --profile core --profile ops up {{build}}

# Pulls prebuilt GHCR images (docker-compose.prod.yml), builds nothing on the host.
# Requires `docker login ghcr.io` first. Pin a build via IMAGE_TAG in .env.

# Server deploy: pull prebuilt images and (re)start
deploy:
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops pull
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops up -d

# ---- CI ----
# Check-only, exactly like the workflow: no --fix and no reformat, so a green
# run here means a green run there. Use `just backend-lint` / `just frontend-lint`
# while developing instead — those auto-fix; this one only reports.
# Actions minutes are billed on this private repo, so running this before
# pushing is the cheapest way to keep them.

# Run every gate from .github/workflows/ci.yml locally
ci:
    cd backend && uv run ruff check src/fanfan tests --respect-gitignore
    cd backend && uv run ruff format --check src/fanfan tests --respect-gitignore
    cd backend && uv run ty check src/fanfan
    cd backend && uv run pytest tests
    cd frontend && pnpm lint
    cd frontend && pnpm check
    cd frontend && pnpm build
    hadolint backend/Dockerfile frontend/Dockerfile

dev:
    @echo "Run in separate terminals:"
    @echo "  just backend-dev"
    @echo "  just frontend-dev"
