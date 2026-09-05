import pytest
from dishka import AsyncContainer
from redis.asyncio import Redis

from fanfan.adapters.redis.rate_limiter import RedisRateLimiter
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import TooManyAttempts

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_hit_sets_ttl_on_first_hit(dishka_request: AsyncContainer):
    limiter = await dishka_request.get(RateLimiter)
    redis = await dishka_request.get(Redis)
    key = "test-ttl-on-first-hit"

    await limiter.hit(key, limit=5, window_seconds=60)

    ttl = await redis.ttl(RedisRateLimiter._counter_key(key))
    assert 0 < ttl <= 60


async def test_hit_raises_once_limit_is_exceeded(dishka_request: AsyncContainer):
    limiter = await dishka_request.get(RateLimiter)
    key = "test-limit-enforced"
    limit = 3

    for _ in range(limit):
        await limiter.hit(key, limit=limit, window_seconds=60)

    with pytest.raises(TooManyAttempts):
        await limiter.hit(key, limit=limit, window_seconds=60)


async def test_hit_self_heals_a_counter_that_lost_its_ttl(
    dishka_request: AsyncContainer,
):
    # Simulates the regression this plan fixes: a counter that was created by
    # INCR alone (e.g. a crash between the old INCR and EXPIRE calls) and so
    # never got a TTL, leaving it to grow forever.
    limiter = await dishka_request.get(RateLimiter)
    redis = await dishka_request.get(Redis)
    key = "test-self-heal-orphaned-counter"
    counter_key = RedisRateLimiter._counter_key(key)

    await redis.incr(counter_key)
    assert await redis.ttl(counter_key) == -1  # no expiry set

    await limiter.hit(key, limit=5, window_seconds=60)

    ttl = await redis.ttl(counter_key)
    assert 0 < ttl <= 60
