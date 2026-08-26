from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.voting.set_voting_time_range import (
    SetVotingTimeRange,
    SetVotingTimeRangeInput,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from tests.fakes.realtime_gateway import FakeRealtimeGateway

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_setting_time_range_persists_and_broadcasts(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingTimeRange)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(voting_manager)

    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)

    await interactor(SetVotingTimeRangeInput(voting_start=start, voting_end=end))

    settings = await settings_gateway.get()
    assert settings.voting_start == start
    assert settings.voting_end == end
    assert [
        (user_id, message.event_name) for user_id, message in realtime.published
    ] == [(None, SSEEventName.CONFIG_UPDATED)]


async def test_no_op_when_range_unchanged_does_not_broadcast(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingTimeRange)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(voting_manager)

    # Both start and end default to None; setting them to None again is a no-op
    # that must neither write nor broadcast.
    await interactor(SetVotingTimeRangeInput(voting_start=None, voting_end=None))

    assert realtime.published == []


async def test_requires_voting_manage(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingTimeRange)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(
            SetVotingTimeRangeInput(
                voting_start=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
                voting_end=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
            )
        )
