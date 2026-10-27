from typing import Any, cast, override

from sqlalchemy import CursorResult, delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fanfan.adapters.db.models import (
    AuthCodeORM,
    AuthSessionORM,
    CooldownORM,
    RateLimitORM,
)
from fanfan.application.ports.expired_state import ExpiredStatePurger

_TABLES = (AuthSessionORM, AuthCodeORM, RateLimitORM, CooldownORM)


class PostgresExpiredStatePurger(ExpiredStatePurger):
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    @override
    async def purge_expired(self) -> int:
        deleted = 0
        async with self.sessions.begin() as session:
            for table in _TABLES:
                result = await session.execute(
                    delete(table).where(table.expires_at <= func.now())
                )
                deleted += cast("CursorResult[Any]", result).rowcount
        return deleted
