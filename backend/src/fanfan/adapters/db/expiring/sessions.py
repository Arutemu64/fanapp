from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine

# A request can hold its unit-of-work connection while it calls these adapters.
# Their own pool means no request waits on one pool twice, so a login rush can't
# starve it (https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing).
# Each statement is a key lookup, so a few connections serve a 1-CPU database.
EXPIRING_POOL_SIZE = 3
EXPIRING_MAX_OVERFLOW = 2


class ExpiringSessionFactory(async_sessionmaker[AsyncSession]):
    """Sessions for the expiring-state adapters, on their own small pool."""


def create_expiring_engine(config: DatabaseConfig) -> AsyncEngine:
    pool_config = config.model_copy(
        update={
            "pool_size": EXPIRING_POOL_SIZE,
            "max_overflow": EXPIRING_MAX_OVERFLOW,
        }
    )
    return create_engine(pool_config)
