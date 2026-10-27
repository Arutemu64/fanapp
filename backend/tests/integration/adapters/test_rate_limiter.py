from datetime import timedelta

import pytest
from dishka import AsyncContainer
from sqlalchemy import func, update

from fanfan.adapters.db.expiring.sessions import ExpiringSessionFactory
from fanfan.adapters.db.models import RateLimitORM
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import TooManyAttempts

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_hit_raises_once_limit_is_exceeded(
    dishka_request: AsyncContainer,
) -> None:
    limiter = await dishka_request.get(RateLimiter)
    key = "test-limit-enforced"
    limit = 3

    for _ in range(limit):
        await limiter.hit(key, limit=limit, window_seconds=60)

    with pytest.raises(TooManyAttempts) as error:
        await limiter.hit(key, limit=limit, window_seconds=60)
    assert 0 < error.value.details["retry_after"] <= 60


async def test_reset_clears_the_counter(dishka_request: AsyncContainer) -> None:
    limiter = await dishka_request.get(RateLimiter)
    key = "test-reset"

    await limiter.hit(key, limit=1, window_seconds=60)
    await limiter.reset(key)

    await limiter.hit(key, limit=1, window_seconds=60)


async def test_hit_starts_a_new_window_once_the_old_one_ends(
    dishka_request: AsyncContainer,
) -> None:
    limiter = await dishka_request.get(RateLimiter)
    sessions = await dishka_request.get(ExpiringSessionFactory)
    key = "test-window-rolls-over"

    await limiter.hit(key, limit=1, window_seconds=60)
    async with sessions.begin() as session:
        await session.execute(
            update(RateLimitORM)
            .where(RateLimitORM.key == key)
            .values(expires_at=func.now() - timedelta(seconds=1))
        )

    await limiter.hit(key, limit=1, window_seconds=60)
