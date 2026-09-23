from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from fanfan.application.ports.run_lease import RunLease


class PostgresRunLease(RunLease):
    """A session-level Postgres advisory lock on a dedicated connection.

    Postgres drops a session-level advisory lock when its connection closes, so
    a worker that dies releases its lease with it — no expiry to tune, unlike a
    heartbeat. The lock lives on its own connection, not the unit of work's
    session: that session hands its connection back to the pool on every
    commit, and a session lock does not end with the transaction
    (https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS).
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._connection: AsyncConnection | None = None
        self._key: UUID | None = None

    async def try_acquire(self, key: UUID) -> bool:
        if self._connection is None:
            self._connection = await self._engine.connect()
        acquired = await self._connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"),
            {"key": str(key)},
        )
        if acquired:
            self._key = key
        return bool(acquired)

    async def release(self) -> None:
        if self._connection is None:
            return
        try:
            if self._key is not None:
                # Unlock before the connection goes back to the pool: a pooled
                # connection outlives this lease and would otherwise keep it.
                await self._connection.execute(
                    text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"),
                    {"key": str(self._key)},
                )
                await self._connection.commit()
        finally:
            await self._connection.close()
            self._connection = None
            self._key = None
