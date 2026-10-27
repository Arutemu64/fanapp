import asyncio
from collections.abc import AsyncIterator
from uuid import uuid7

import pytest
import pytest_asyncio
from dishka import AsyncContainer
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fanfan.adapters.db.expiring.rate_limiter import PostgresRateLimiter
from fanfan.adapters.db.expiring.session_store import PostgresSessionStore
from fanfan.adapters.db.expiring.sessions import ExpiringSessionFactory
from fanfan.adapters.db.gateways.users import SqlUserGateway
from fanfan.adapters.db.models import UserORM
from fanfan.adapters.db.uow import SqlUnitOfWork
from fanfan.core.exceptions.rate_limit import TooManyAttempts
from fanfan.core.vo.user import UserId

# These tests use real, separate connections, as production does. The usual
# rollback fixture shares one connection and would hide lock conflicts.

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

_SECONDS_TO_HANG = 5


@pytest_asyncio.fixture
async def engine(dishka: AsyncContainer) -> AsyncEngine:
    return await dishka.get(AsyncEngine)


@pytest_asyncio.fixture
async def committed_user(engine: AsyncEngine) -> AsyncIterator[UserId]:
    user_id = UserId(uuid7())
    async with engine.begin() as connection:
        await connection.execute(
            insert(UserORM).values(
                id=user_id,
                username=f"lock-{user_id.hex[:8]}",
                avatar_seed="seed",
                number=int(user_id.int % 900_000) + 100_000,
                settings={},
            )
        )
    yield user_id
    async with engine.begin() as connection:
        await connection.execute(delete(UserORM).where(UserORM.id == user_id))


async def test_session_is_created_while_the_login_holds_the_user_row(
    engine: AsyncEngine, committed_user: UserId
) -> None:
    store = PostgresSessionStore(
        ExpiringSessionFactory(engine), ttl_seconds=60, touch_threshold_seconds=30
    )
    async with AsyncSession(engine) as login_session:
        gateway = SqlUserGateway(login_session, SqlUnitOfWork(login_session))
        assert await gateway.get_by_id(committed_user) is not None

        session_id = await asyncio.wait_for(
            store.create_session(committed_user), timeout=_SECONDS_TO_HANG
        )

        resolution = await store.resolve_session(session_id)
        assert resolution.user_id == committed_user


async def test_hit_survives_the_caller_rolling_back(engine: AsyncEngine) -> None:
    limiter = PostgresRateLimiter(ExpiringSessionFactory(engine))
    key = f"test-survives-rollback-{uuid7()}"
    try:
        async with AsyncSession(engine) as caller:
            await caller.execute(select(1))
            await limiter.hit(key, limit=1, window_seconds=60)
            await caller.rollback()

        with pytest.raises(TooManyAttempts):
            await limiter.hit(key, limit=1, window_seconds=60)
    finally:
        await limiter.reset(key)
