import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from fanfan.adapters.config.parsers import get_database_config
from fanfan.adapters.db.event_loop import loop_factory
from fanfan.adapters.db.models import BaseORM

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseORM.metadata

DEFAULT_ALEMBIC_DATABASE_URL = "driver://user:pass@localhost/dbname"

AUTOGENERATE_PLUGINS = ["alembic.autogenerate.*", "alembic.ext.checkconstraint_byname"]

MIGRATION_LOCK_TIMEOUT = "5s"


def get_database_url() -> str:
    alembic_url = config.get_main_option("sqlalchemy.url")
    if alembic_url and alembic_url != DEFAULT_ALEMBIC_DATABASE_URL:
        return alembic_url

    return get_database_config().build_connection_str()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        autogenerate_plugins=AUTOGENERATE_PLUGINS,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        autogenerate_plugins=AUTOGENERATE_PLUGINS,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {}).copy()
    section["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"options": f"-c lock_timeout={MIGRATION_LOCK_TIMEOUT}"},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations(), loop_factory=loop_factory())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
