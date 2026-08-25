from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.voting.set_voting_enabled import (
    SetVotingEnabled,
    SetVotingEnabledInput,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from tests.fakes.realtime_gateway import FakeRealtimeGateway

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_enabling_voting_persists_and_broadcasts(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingEnabled)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(voting_manager)

    await interactor(SetVotingEnabledInput(enabled=True))

    assert (await settings_gateway.get()).voting_enabled is True
    # Voting availability rides CONFIG_UPDATED so open clients refetch state.
    assert [
        (user_id, message.event_name) for user_id, message in realtime.published
    ] == [(None, SSEEventName.CONFIG_UPDATED)]


async def test_no_op_when_state_unchanged_does_not_broadcast(
    dishka_request: AsyncContainer,
    voting_manager: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingEnabled)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(voting_manager)

    # Voting starts disabled by default; disabling it again is a no-op that must
    # neither write nor broadcast a redundant refetch.
    await interactor(SetVotingEnabledInput(enabled=False))

    assert realtime.published == []


async def test_requires_voting_manage(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(SetVotingEnabled)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(SetVotingEnabledInput(enabled=True))
