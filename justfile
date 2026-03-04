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

frontend-generate-api:
	cd frontend && pnpm generate-api

# ---- Backend (FastAPI + uv) ----
backend-install:
	cd backend && uv sync --all-groups

backend-dev:
	cd backend && uv run python -m fanfan.main.web

backend-format:
	cd backend && uv run ruff format src/fanfan --respect-gitignore

backend-check:
	cd backend && uv run ruff check src/fanfan --respect-gitignore --fix --unsafe-fixes

backend-lint: backend-format backend-check

backend-migrate:
	cd backend && uv run alembic upgrade head && uv run python -m fanfan.main.migration

backend-generate MIGRATION_NAME:
	cd backend && uv run alembic revision --autogenerate -m "{{MIGRATION_NAME}}"

# ---- Docker infra helpers ----
infra-up-web:
	docker compose --profile web up -d db redis migration web

infra-logs-web:
	docker compose logs -f web db redis migration

infra-stop-web:
	docker compose stop web db redis migration

# ---- Aggregates ----
install: frontend-install backend-install

lint: frontend-lint backend-lint

check: frontend-check backend-check

dev:
	@echo "Run in separate terminals:"
	@echo "  just backend-dev"
	@echo "  just frontend-dev"