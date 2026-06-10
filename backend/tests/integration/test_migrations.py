from alembic.command import check
from alembic.config import Config as AlembicConfig


# This test must stay synchronous (a plain `def`, not async): the Alembic
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
