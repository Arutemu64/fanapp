#!/usr/bin/env python3
#
# Autogenerate an Alembic migration against a throwaway Postgres container
# (same image as the drift test and CI). Boots a temporary database, applies
# existing migrations, autogenerates the diff against the ORM models, then
# tears the container down. Driven by `just backend-generate-auto <name>`.
#
# Use where no app database is running (e.g. Claude Code on the web). Needs
# Docker. Pure Python via testcontainers — same container mechanism as the
# migration drift test (tests/fixtures/db_provider.py), so it runs the same on
# Linux, macOS and Windows with no bash/docker-CLI scripting.
#
# Always REVIEW the generated file — autogenerate misses column renames and may
# get server-default / enum-value changes wrong.
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from testcontainers.postgres import PostgresContainer

# This file lives at backend/scripts/; alembic.ini and the migrations package
# sit under the backend root, one level up.
BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "src" / "fanfan" / "adapters" / "db" / "migrations"

# Pinned (not a floating minor tag) to match production (docker-compose.yml),
# the integration test suite (tests/fixtures/db_provider.py), and the cloud
# prepull (.claude/setup.sh) exactly — a different image risks false diffs
# (e.g. server-default rendering) — and the cloud session reuses the prepulled
# image instead of lazy-pulling another.
POSTGRES_IMAGE = "postgres:18.6-alpine"

# argv is [script_path, migration_name] — exactly two entries when called right.
EXPECTED_ARGC = 2


def build_alembic_config(connection_url: str) -> AlembicConfig:
    # Mirrors the alembic_config test fixture: load alembic.ini, then point it
    # at the throwaway database. env.py reads sqlalchemy.url once it differs
    # from the .ini placeholder, so no full app config is loaded.
    config = AlembicConfig(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", connection_url)
    return config


def main() -> None:
    if len(sys.argv) != EXPECTED_ARGC or not sys.argv[1].strip():
        sys.exit("usage: generate_migration.py <migration_name>")
    migration_name = sys.argv[1]

    # asyncpg driver: env.py builds an async engine, matching runtime and tests.
    postgres = PostgresContainer(POSTGRES_IMAGE, driver="asyncpg")
    # Workaround from testcontainers/testcontainers-python#108 (same as the
    # db_provider test fixture); without it the host is misresolved on Windows.
    if os.name == "nt":
        postgres.get_container_host_ip = lambda: "localhost"

    postgres.start()
    try:
        config = build_alembic_config(postgres.get_connection_url())
        command.upgrade(config, "head")
        command.revision(config, message=migration_name, autogenerate=True)
    finally:
        postgres.stop()


if __name__ == "__main__":
    main()
