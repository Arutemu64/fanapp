import pytest
from dishka import AsyncContainer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fanfan.adapters.db.gateways.schedule_events import (
    SCHEDULE_EDIT_LOCK_KEY,
    SqlScheduleEventGateway,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _rival_can_lock(engine: AsyncEngine) -> bool:
    async with engine.connect() as rival:
        acquired = await rival.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": SCHEDULE_EDIT_LOCK_KEY},
        )
        await rival.rollback()
    return bool(acquired)


async def test_edit_lock_is_held_until_the_transaction_ends(
    dishka_request: AsyncContainer,
) -> None:
    # Undo and import take no rate lock, so this lock alone keeps them from
    # computing an order against neighbours a concurrent move is changing.
    # Its own session, not the test fixture's: that one never really commits.
    engine = await dishka_request.get(AsyncEngine)
    async with AsyncSession(engine) as session:
        await SqlScheduleEventGateway(session).lock_for_edit()
        assert not await _rival_can_lock(engine)

        await session.commit()
        assert await _rival_can_lock(engine)
