import math
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import override

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from fanfan.adapters.db.expiring.sessions import ExpiringSessionFactory
from fanfan.adapters.db.models import CooldownORM
from fanfan.application.ports.cooldown import Cooldown
from fanfan.core.exceptions.rate_limit import CooldownActive


class PostgresCooldown(Cooldown):
    """One row per window; the upsert both serializes callers and starts it.

    The upsert takes over a row only once its window has passed, so of two
    concurrent claims exactly one gets a row back. Time comes from the database
    clock alone.
    """

    def __init__(self, sessions: ExpiringSessionFactory) -> None:
        self.sessions = sessions

    @override
    @asynccontextmanager
    async def claim(self, key: str, seconds: int) -> AsyncIterator[None]:
        token = secrets.token_hex(16)
        if not await self._take(key, token, seconds):
            raise CooldownActive(retry_after=await self._retry_after(key))
        try:
            yield
        except BaseException:
            await self._give_back(key, token)
            raise

    async def _take(self, key: str, token: str, seconds: int) -> bool:
        expires_at = func.now() + timedelta(seconds=max(1, seconds))
        statement = (
            insert(CooldownORM)
            .values(key=key, token=token, expires_at=expires_at)
            .on_conflict_do_update(
                index_elements=[CooldownORM.key],
                set_={"token": token, "expires_at": expires_at},
                where=CooldownORM.expires_at <= func.now(),
            )
            .returning(CooldownORM.key)
        )
        async with self.sessions.begin() as session:
            return (await session.execute(statement)).first() is not None

    async def _retry_after(self, key: str) -> int:
        async with self.sessions.begin() as session:
            seconds_left = await session.scalar(
                select(
                    func.extract("epoch", CooldownORM.expires_at - func.now())
                ).where(CooldownORM.key == key)
            )
        return max(1, math.ceil(seconds_left or 0))

    async def _give_back(self, key: str, token: str) -> None:
        """Delete the claim only if it is still ours, not a newer one's."""
        async with self.sessions.begin() as session:
            await session.execute(
                delete(CooldownORM).where(
                    CooldownORM.key == key, CooldownORM.token == token
                )
            )
