#!/usr/bin/env bash
#
# Autogenerate an Alembic migration against a throwaway Postgres 18 container
# (matches production and CI). Boots a temporary database, applies existing
# migrations, autogenerates the diff against the ORM models, then removes the
# container. Needs Docker; use where no app database is running (e.g. Claude
# Code on the web). Driven by `just backend-generate-auto <name>`.
#
# Always REVIEW the generated file — autogenerate misses column renames and may
# get server-default / enum-value changes wrong.
set -euo pipefail

migration_name="${1:?usage: generate-migration.sh <migration_name>}"

container="fanfan-alembic-$$"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --rm --name "$container" \
  -e POSTGRES_USER=fanfan -e POSTGRES_PASSWORD=fanfan -e POSTGRES_DB=fanfan \
  -p 5433:5432 postgres:18-alpine >/dev/null

# Wait until Postgres accepts connections before running Alembic.
for _ in $(seq 1 30); do
  if docker exec "$container" pg_isready -U fanfan -q; then break; fi
  sleep 1
done

# Scoped override read by migrations/env.py — avoids loading the full app config.
export ALEMBIC_DATABASE_URL="postgresql+asyncpg://fanfan:fanfan@localhost:5433/fanfan"

uv run alembic upgrade head
uv run alembic revision --autogenerate -m "$migration_name"
