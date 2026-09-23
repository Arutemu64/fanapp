import asyncio
from collections.abc import AsyncIterator
from uuid import uuid7

import pytest
from dishka import AsyncContainer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.factory import create_engine
from fanfan.adapters.db.run_lease import PostgresRunLease

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


@pytest.fixture
async def short_idle_engine(dishka: AsyncContainer) -> AsyncIterator[AsyncEngine]:
    # The production safety timeout (60 s) shortened, so a test can outlast it.
    config = await dishka.get(DatabaseConfig)
    engine = create_engine(
        config.model_copy(update={"idle_in_transaction_session_timeout": 500})
    )
    yield engine
    await engine.dispose()


async def test_lease_outlives_the_idle_in_transaction_timeout(
    short_idle_engine: AsyncEngine,
) -> None:
    # A sync holds its lease far longer than the idle-in-transaction timeout. If
    # the lease connection sat inside an open transaction, Postgres would kill
    # it and silently hand the run to a second worker mid-sync.
    run_id = uuid7()
    holder = PostgresRunLease(short_idle_engine)
    rival = PostgresRunLease(short_idle_engine)
    try:
        assert await holder.try_acquire(run_id)
        await asyncio.sleep(1)
        assert not await rival.try_acquire(run_id)
    finally:
        await rival.release()
        await holder.release()


async def test_lease_frees_when_the_holder_connection_dies(
    short_idle_engine: AsyncEngine,
) -> None:
    # No expiry to tune: a crashed worker's connection closes and Postgres
    # drops its lock at once, so the run can be resumed immediately.
    run_id = uuid7()
    holder = PostgresRunLease(short_idle_engine)
    rival = PostgresRunLease(short_idle_engine)
    try:
        assert await holder.try_acquire(run_id)
        # Kill only the holder's own backend, standing in for its crash; other
        # sessions on the shared test database must not be touched.
        assert holder._connection is not None
        holder_pid = await holder._connection.scalar(text("SELECT pg_backend_pid()"))
        async with short_idle_engine.connect() as admin:
            await admin.execute(
                text("SELECT pg_terminate_backend(:pid)"), {"pid": holder_pid}
            )
        assert await rival.try_acquire(run_id)
    finally:
        await rival.release()
        # Releasing a lease whose connection already died is a quiet no-op.
        await holder.release()
