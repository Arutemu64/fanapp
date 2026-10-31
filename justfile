set default-list

# Compatibility names; use dev and backend-check in new documentation.
alias run-dev := dev
alias backend-lint := backend-check

# Install project dependencies and create local configuration without replacing it.
[group("development")]
setup: backend-install frontend-install bootstrap

# Start the full Docker development stack with hot reload.
[arg("build", long, value="true")]
[group("development")]
dev build="false":
    docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile core up {{ if build == "true" { "--build" } else { "" } }} --watch

# Run after `just dev` starts, in another terminal. Seeds an empty local database.
[group("development")]
demo:
    docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile core exec api cli demo seed

[group("development")]
bootstrap:
    cd backend && uv run --locked python scripts/bootstrap.py

[group("development")]
run-infra:
    docker compose up -d db nats

[group("development")]
stop-infra:
    docker compose stop db nats

[group("development")]
backend-install:
    cd backend && uv sync --all-groups --locked

[group("development")]
frontend-install:
    cd frontend && pnpm install --frozen-lockfile

[group("development")]
backend-dev:
    cd backend && uv run --locked python -m fanfan.main.web

[group("development")]
backend-worker:
    cd backend && uv run --locked faststream run --factory --reload --port 8001 fanfan.main.worker:create_app

[group("development")]
frontend-dev:
    cd frontend && pnpm dev

[group("development")]
backend-setup-hooks:
    cd backend && uv run --locked prek install --force

# Check backend formatting, lint, types and import boundaries; change no source files.
[group("checks")]
backend-check: _backend-lint backend-typecheck backend-import-lint

# Check frontend formatting, lint and types; change no source files.
[group("checks")]
frontend-check: frontend-lint frontend-typecheck

[group("checks")]
backend-typecheck:
    cd backend && uv run --locked ty check

[group("checks")]
frontend-typecheck:
    cd frontend && pnpm check

[group("checks")]
frontend-lint:
    cd frontend && pnpm lint

[group("checks")]
backend-import-lint:
    cd backend && uv run --locked lint-imports

[group("checks")]
root-lint:
    frontend/node_modules/.bin/prettier --check "**/*.{md,yml,yaml}"

[group("checks")]
dockerfile-lint:
    hadolint backend/Dockerfile frontend/Dockerfile

[group("checks")]
backend-deadcode:
    cd backend && uv run --locked vulture

[group("checks")]
frontend-deadcode:
    cd frontend && pnpm deadcode

[group("formatting")]
backend-format:
    cd backend && uv run --locked ruff format src/fanfan tests scripts --respect-gitignore

# Sort dependencies, apply Ruff fixes, then format Python.
[group("formatting")]
backend-fix: backend-sort-deps && backend-format
    cd backend && uv run --locked ruff check src/fanfan tests scripts --respect-gitignore --fix

[group("formatting")]
backend-sort-deps:
    cd backend && uv run --locked uv-sort

[group("formatting")]
frontend-format:
    cd frontend && pnpm format

[group("formatting")]
root-format:
    frontend/node_modules/.bin/prettier --write "**/*.{md,yml,yaml}"

# Run backend unit tests without Docker.
[group("tests")]
backend-test:
    cd backend && uv run --locked pytest tests -m unit

# Run all backend tests with coverage (requires Docker).
[group("tests")]
backend-test-cov:
    cd backend && uv run --locked pytest tests --cov --cov-report=term-missing

# Run backend integration tests (requires Docker).
[group("tests")]
backend-test-integration:
    cd backend && uv run --locked pytest tests/integration

# Check migration drift and downgrade behavior (requires Docker).
[group("tests")]
backend-check-migrations:
    cd backend && uv run --locked pytest tests/integration/test_migrations.py

[group("tests")]
frontend-test:
    cd frontend && pnpm test

# Run Playwright against a production build with a mocked backend.
[group("tests")]
frontend-e2e:
    cd frontend && pnpm e2e

[group("tests")]
frontend-e2e-ui:
    cd frontend && pnpm e2e:ui

[group("tests")]
frontend-e2e-webkit:
    cd frontend && pnpm e2e --project=mobile-webkit

[group("tests")]
frontend-e2e-install-webkit:
    cd frontend && pnpm exec playwright install --with-deps webkit

[group("generation")]
frontend-generate-api: backend-generate-openapi
    cd frontend && pnpm generate-api

# Regenerate the API client and fail on tracked changes.
[group("generation")]
frontend-check-api:
    cd frontend && pnpm generate-api:check

[group("generation")]
backend-generate-openapi:
    cd backend && uv run --locked python -m fanfan.main.generate_openapi

[group("generation")]
backend-generate-vapid:
    cd backend && uv run --locked generate-vapid

# Autogenerate a migration against the configured database; review the result.
[group("generation")]
backend-generate migration_name:
    cd backend && uv run --locked alembic revision --autogenerate -m {{ quote(migration_name) }}

# Autogenerate a migration against a disposable Postgres; review the result.
[group("generation")]
backend-generate-auto migration_name:
    cd backend && uv run --locked python scripts/generate_migration.py {{ quote(migration_name) }}

[group("generation")]
backend-generate-schedule-template:
    cd backend && uv run --locked python scripts/generate_schedule_template.py

[group("generation")]
readme-gallery:
    cd frontend && pnpm exec playwright test -c playwright.gallery.config.ts

# Apply migrations to the configured database.
[group("operations")]
backend-migrate:
    cd backend && uv run --locked alembic upgrade head

# Seed demo data through the host CLI; use demo for the Docker stack.
[group("operations")]
backend-seed-demo:
    cd backend && uv run --locked python -m fanfan.main.cli demo seed

[group("operations")]
backend-sync target:
    cd backend && uv run --locked python -m fanfan.main.cli sync {{ quote(target) }}

[group("operations")]
frontend-build:
    cd frontend && pnpm build

# Build and run production images locally, including backups.
[arg("no_build", long="no-build", value="true")]
[group("operations")]
run-prod no_build="false": _backups-dir
    APP_VERSION="$(cd backend && uv version --short)" docker compose -f docker-compose.yml --profile core --profile ops up {{ if no_build == "true" { "--no-build" } else { "--build" } }}

# Pull published images and restart the deployed stack.
[group("operations")]
deploy: _backups-dir
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops pull
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops up -d --wait --wait-timeout 300 --remove-orphans

_backups-dir:
    mkdir -p backups
    chmod 700 backups

_backend-lint:
    cd backend && uv run --locked uv-sort --check
    cd backend && uv run --locked ruff format --check src/fanfan tests scripts --respect-gitignore
    cd backend && uv run --locked ruff check src/fanfan tests scripts --respect-gitignore
