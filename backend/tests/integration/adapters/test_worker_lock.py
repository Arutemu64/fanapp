import asyncio
from collections.abc import AsyncIterator

import pytest
from dishka import AsyncContainer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine
from fanfan.adapters.db.worker_lock import PostgresWorkerLock

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


@pytest.fixture
async def short_idle_engine(dishka: AsyncContainer) -> AsyncIterator[AsyncEngine]:
    config = await dishka.get(DatabaseConfig)
    engine = create_engine(
        config.model_copy(update={"idle_in_transaction_session_timeout": 500})
    )
    yield engine
    await engine.dispose()


async def test_lock_outlives_the_idle_in_transaction_timeout(
    short_idle_engine: AsyncEngine,
) -> None:
    key = "test:worker-lock"
    holder = PostgresWorkerLock(short_idle_engine)
    rival = PostgresWorkerLock(short_idle_engine)
    try:
        assert await holder.try_acquire(key)
        await asyncio.sleep(1)
        assert not await rival.try_acquire(key)
    finally:
        await rival.release()
        await holder.release()


async def test_lock_frees_when_the_holder_connection_dies(
    short_idle_engine: AsyncEngine,
) -> None:
    key = "test:worker-lock"
    holder = PostgresWorkerLock(short_idle_engine)
    rival = PostgresWorkerLock(short_idle_engine)
    try:
        assert await holder.try_acquire(key)
        assert holder._connection is not None
        holder_pid = await holder._connection.scalar(text("SELECT pg_backend_pid()"))
        async with short_idle_engine.connect() as admin:
            await admin.execute(
                text("SELECT pg_terminate_backend(:pid)"), {"pid": holder_pid}
            )
        assert await rival.try_acquire(key)
    finally:
        await rival.release()
        await holder.release()
