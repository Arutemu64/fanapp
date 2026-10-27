#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from testcontainers.postgres import PostgresContainer

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "src" / "fanfan" / "adapters" / "db" / "migrations"

POSTGRES_IMAGE = "postgres:18.6-alpine"

EXPECTED_ARGC = 2


def build_alembic_config(connection_url: str) -> AlembicConfig:
    config = AlembicConfig(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", connection_url)
    return config


def main() -> None:
    if len(sys.argv) != EXPECTED_ARGC or not sys.argv[1].strip():
        sys.exit("usage: generate_migration.py <migration_name>")
    migration_name = sys.argv[1]

    postgres = PostgresContainer(POSTGRES_IMAGE, driver="psycopg")
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
