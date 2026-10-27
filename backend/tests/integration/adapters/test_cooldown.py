import pytest
from dishka import AsyncContainer
from sqlalchemy import update

from fanfan.adapters.db.expiring.sessions import ExpiringSessionFactory
from fanfan.adapters.db.models import CooldownORM
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
    cooldown = await dishka_request.get(Cooldown)
    sessions = await dishka_request.get(ExpiringSessionFactory)

    async def send_that_outlives_its_window() -> None:
        async with cooldown.claim("test-reclaimed", 60):
            async with sessions.begin() as session:
                await session.execute(
                    update(CooldownORM)
                    .where(CooldownORM.key == "test-reclaimed")
                    .values(token="someone-else")
                )
            raise SendFailed

    with pytest.raises(SendFailed):
        await send_that_outlives_its_window()

    with pytest.raises(CooldownActive):
        async with cooldown.claim("test-reclaimed", 60):
            pass
