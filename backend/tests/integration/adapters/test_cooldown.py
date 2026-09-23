import pytest
from dishka import AsyncContainer
from redis.asyncio import Redis

from fanfan.adapters.redis.cooldown import RedisCooldown
from fanfan.application.ports.cooldown import Cooldown
from fanfan.core.exceptions.rate_limit import CooldownActive

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


class SendFailed(Exception):
    pass


async def test_second_claim_within_the_window_is_rejected(
    dishka_request: AsyncContainer,
) -> None:
    cooldown = await dishka_request.get(Cooldown)

    async with cooldown.claim("test-window", 60):
        pass

    with pytest.raises(CooldownActive) as error:
        async with cooldown.claim("test-window", 60):
            pass
    assert 0 < error.value.details["retry_after"] <= 60


async def test_concurrent_claim_fails_fast_while_the_first_runs(
    dishka_request: AsyncContainer,
) -> None:
    # A second request during an in-flight send must not queue behind it.
    cooldown = await dishka_request.get(Cooldown)

    async with cooldown.claim("test-in-flight", 60):
        with pytest.raises(CooldownActive):
            async with cooldown.claim("test-in-flight", 60):
                pass


async def test_failed_block_gives_the_claim_back(
    dishka_request: AsyncContainer,
) -> None:
    cooldown = await dishka_request.get(Cooldown)

    with pytest.raises(SendFailed):
        async with cooldown.claim("test-failure", 60):
            raise SendFailed

    async with cooldown.claim("test-failure", 60):
        pass


async def test_failed_block_leaves_a_newer_claim_alone(
    dishka_request: AsyncContainer,
) -> None:
    # The block outlived its window and another caller claimed the key; the
    # failing block must not delete that newer claim on its way out.
    cooldown = await dishka_request.get(Cooldown)
    redis = await dishka_request.get(Redis)
    redis_key = RedisCooldown._redis_key("test-reclaimed")

    async def send_that_outlives_its_window() -> None:
        async with cooldown.claim("test-reclaimed", 60):
            await redis.set(redis_key, "someone-else", ex=60)
            raise SendFailed

    with pytest.raises(SendFailed):
        await send_that_outlives_its_window()

    assert await redis.get(redis_key) in ("someone-else", b"someone-else")
