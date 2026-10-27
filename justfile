bootstrap:
    cd backend && uv run python scripts/bootstrap.py

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

frontend-test:
    cd frontend && pnpm test

frontend-deadcode:
    cd frontend && pnpm deadcode

frontend-e2e:
    cd frontend && pnpm e2e

frontend-e2e-install-webkit:
    cd frontend && pnpm exec playwright install --with-deps webkit

frontend-e2e-webkit:
    cd frontend && pnpm e2e --project=mobile-webkit

frontend-e2e-ui:
    cd frontend && pnpm e2e:ui

readme-gallery:
    cd frontend && pnpm exec playwright test -c playwright.gallery.config.ts

frontend-generate-api: backend-generate-openapi
    cd frontend && pnpm generate-api

frontend-check-api:
    cd frontend && pnpm generate-api:check

backend-install:
    cd backend && uv sync --all-groups

backend-setup-hooks:
    cd backend && uv run prek install --force

backend-dev:
    cd backend && uv run python -m fanfan.main.web

backend-worker:
    cd backend && uv run faststream run --factory --reload --port 8001 fanfan.main.worker:create_app

backend-generate-openapi:
    cd backend && uv run python -m fanfan.main.generate_openapi

backend-generate-vapid:
    cd backend && uv run generate-vapid

backend-format:
    cd backend && uv run ruff format src/fanfan tests scripts --respect-gitignore

backend-check:
    cd backend && uv run ruff check src/fanfan tests scripts --respect-gitignore --fix

backend-test:
    cd backend && uv run pytest tests -m unit

backend-test-cov:
    cd backend && uv run pytest tests --cov --cov-report=term-missing

backend-test-integration:
    cd backend && uv run pytest tests/integration

backend-sync TARGET:
    cd backend && uv run python -m fanfan.main.cli sync {{ TARGET }}

backend-seed-demo:
    cd backend && uv run python -m fanfan.main.cli demo seed

backend-typecheck:
    cd backend && uv run ty check

backend-deadcode:
    cd backend && uv run vulture

backend-import-lint:
    cd backend && uv run lint-imports

backend-sort-deps:
    cd backend && uv run uv-sort

backend-lint: backend-sort-deps backend-format backend-check backend-typecheck backend-import-lint

backend-migrate:
    cd backend && uv run alembic upgrade head

backend-generate MIGRATION_NAME:
    cd backend && uv run alembic revision --autogenerate -m "{{ MIGRATION_NAME }}"

backend-generate-auto MIGRATION_NAME:
    cd backend && uv run python scripts/generate_migration.py "{{ MIGRATION_NAME }}"

backend-generate-schedule-template:
    cd backend && uv run python scripts/generate_schedule_template.py

backend-check-migrations:
    cd backend && uv run pytest tests/integration/test_migrations.py

dockerfile-lint:
    hadolint backend/Dockerfile frontend/Dockerfile

run-infra:
    docker compose up -d db redis nats

stop-infra:
    docker compose stop db redis nats

run-dev build="":
    docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile core up {{build}} --watch

run-prod build="--build": _backups-dir
    APP_VERSION="$(cd backend && uv version --short)" docker compose -f docker-compose.yml --profile core --profile ops up {{build}}

deploy: _backups-dir
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops pull
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile core --profile ops up -d --wait --wait-timeout 300 --remove-orphans

_backups-dir:
    mkdir -p backups
    chmod 700 backups

dev:
    @echo "Run in separate terminals:"
    @echo "  just backend-dev"
    @echo "  just backend-worker"
    @echo "  just frontend-dev"
