# =========================
# Monorepo helper commands
# =========================
# No workspaces: frontend and backend keep isolated dependency trees.

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

backend-format:
    cd backend && uv run ruff format src/fanfan tests --respect-gitignore

backend-check:
    cd backend && uv run ruff check src/fanfan tests --respect-gitignore --fix --unsafe-fixes

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
    cd backend && ./scripts/generate-migration.sh "{{ MIGRATION_NAME }}"

# Fail if ORM models drift from migrations (spins a throwaway Postgres via testcontainers)
backend-check-migrations:
    cd backend && uv run pytest tests/integration/test_migrations.py

# ---- Docker infra helpers ----
# Pass build="" to skip image rebuild (default rebuilds)
run-dev build="--build":
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

dev:
    @echo "Run in separate terminals:"
    @echo "  just backend-dev"
    @echo "  just frontend-dev"
