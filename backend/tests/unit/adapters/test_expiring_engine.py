import pytest
from pydantic import PostgresDsn
from sqlalchemy.pool import QueuePool

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.expiring.sessions import (
    EXPIRING_MAX_OVERFLOW,
    EXPIRING_POOL_SIZE,
    create_expiring_engine,
)

pytestmark = pytest.mark.unit


async def test_expiring_engine_has_its_own_small_pool() -> None:
    config = DatabaseConfig(
        url=PostgresDsn("postgresql+psycopg://u:p@localhost/db"),
        pool_size=10,
        max_overflow=10,
    )

    engine = create_expiring_engine(config)
    try:
        pool = engine.sync_engine.pool
        assert isinstance(pool, QueuePool)
        assert pool.size() == EXPIRING_POOL_SIZE
        assert pool._max_overflow == EXPIRING_MAX_OVERFLOW
    finally:
        await engine.dispose()
