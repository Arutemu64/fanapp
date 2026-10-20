import pytest
from alembic.command import check, downgrade, upgrade
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, make_url, text

ROUND_TRIP_DATABASE = "migration_round_trip"


# These tests must stay synchronous (a plain `def`, not async): the Alembic
# env.py runs migrations via `asyncio.run(...)`, which fails if called from
# inside an already-running event loop (as an async test would have).
def test_no_migration_drift(alembic_config: AlembicConfig) -> None:
    """Fail if the ORM models drift from the migrations.

    `upgrade_schema_db` (autouse) has already brought the test database up to
    `head`. `alembic check` then autogenerates a diff between the ORM metadata
    (BaseORM.metadata) and that schema; if anything differs, the models were
    changed without a matching migration and it raises, failing this test.

    Fix a failure by generating the missing migration:
        just backend-generate <name>
    """
    check(alembic_config)


@pytest.fixture
def round_trip_alembic_config(alembic_config: AlembicConfig) -> AlembicConfig:
    # A database of its own in the same container: the round trip drops every
    # table, and the session database the other integration tests share must
    # stay at head.
    session_url = make_url(alembic_config.get_main_option("sqlalchemy.url", ""))
    engine = create_engine(session_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {ROUND_TRIP_DATABASE}"))
    engine.dispose()

    round_trip_url = session_url.set(database=ROUND_TRIP_DATABASE)
    config = AlembicConfig(alembic_config.config_file_name)
    config.set_main_option(
        "script_location", alembic_config.get_main_option("script_location", "")
    )
    config.set_main_option(
        "sqlalchemy.url", round_trip_url.render_as_string(hide_password=False)
    )
    return config


def test_migrations_round_trip(round_trip_alembic_config: AlembicConfig) -> None:
    """Fail if any migration's downgrade() is broken.

    A "stairway": for each revision from base to head, upgrade to it, downgrade
    one step, and upgrade again. Each downgrade runs against the exact schema
    its own upgrade produced, so a failure names the revision at fault (see the
    captured "Running downgrade" log), and the re-upgrade catches a downgrade
    that leaves behind something its upgrade then trips over. The closing
    `check` catches residue autogenerate can see but no upgrade collides with.
    """
    config = round_trip_alembic_config
    revisions = list(
        ScriptDirectory.from_config(config).walk_revisions("base", "heads")
    )
    for revision in reversed(revisions):
        upgrade(config, revision.revision)
        downgrade(config, "-1")
        upgrade(config, revision.revision)
    check(config)
