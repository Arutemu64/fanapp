from typing import override

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncEngine

from fanfan.adapters.db.models import (
    AuthCodeORM,
    AuthSessionORM,
    CooldownORM,
    RateLimitORM,
)
from fanfan.application.ports.expired_state import ExpiredStatePurger

_TABLES = (AuthSessionORM, AuthCodeORM, RateLimitORM, CooldownORM)


class PostgresExpiredStatePurger(ExpiredStatePurger):
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    @override
    async def purge_expired(self) -> int:
        deleted = 0
        async with self.engine.begin() as connection:
            for table in _TABLES:
                result = await connection.execute(
                    delete(table).where(table.expires_at <= func.now())
                )
                deleted += result.rowcount
        return deleted
