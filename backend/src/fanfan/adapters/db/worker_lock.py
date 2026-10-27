from typing import override

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from fanfan.application.ports.worker_lock import WorkerLock


class PostgresWorkerLock(WorkerLock):
    """A session-level Postgres advisory lock on a dedicated connection.

    Postgres drops a session-level advisory lock when its connection closes, so
    a worker that dies releases its lock with it — no expiry to tune, unlike a
    heartbeat. The lock lives on its own connection, not the unit of work's
    session: that session hands its connection back to the pool on every
    commit, and a session lock does not end with the transaction
    (https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS).
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._connection: AsyncConnection | None = None
        self._key: str | None = None

    @override
    async def try_acquire(self, key: str) -> bool:
        if self._connection is None:
            self._connection = await self._engine.connect()
        acquired = await self._connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"),
            {"key": key},
        )
        await self._connection.commit()
        if acquired:
            self._key = key
        return bool(acquired)

    @override
    async def release(self) -> None:
        if self._connection is None:
            return
        try:
            if self._key is not None:
                await self._connection.execute(
                    text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"),
                    {"key": self._key},
                )
                await self._connection.commit()
        except DBAPIError:
            pass
        finally:
            await self._connection.close()
            self._connection = None
            self._key = None
