from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine

EXPIRING_POOL_SIZE = 3
EXPIRING_MAX_OVERFLOW = 2


class ExpiringSessionFactory(async_sessionmaker[AsyncSession]):
    """Sessions for the expiring-state adapters, on their own small pool.

    A request may hold its unit-of-work connection while it calls these
    adapters, so a shared pool could starve under a login rush (ADR-0047).
    """


def create_expiring_engine(config: DatabaseConfig) -> AsyncEngine:
    pool_config = config.model_copy(
        update={
            "pool_size": EXPIRING_POOL_SIZE,
            "max_overflow": EXPIRING_MAX_OVERFLOW,
        }
    )
    return create_engine(pool_config)
