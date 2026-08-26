from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
    UpdateSettings,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import InvalidFestivalTimeRange
from fanfan.core.models.user import User
from tests.fakes.realtime_gateway import FakeRealtimeGateway

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_public_field_change_broadcasts_config_updated(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(settings_editor)

    new_end = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)
    await interactor(UpdateAppSettingsInput(festival_end=new_end))

    assert (await settings_gateway.get()).festival_end == new_end
    # A single broadcast (user_id=None) so every open home page refetches /config.
    assert [
        (user_id, message.event_name) for user_id, message in realtime.published
    ] == [(None, SSEEventName.CONFIG_UPDATED)]


async def test_festival_end_before_start_is_rejected(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    login(settings_editor)

    # Partial update touching only the end: it must be validated against the
    # persisted start, not accepted in isolation.
    original_end = (await settings_gateway.get()).festival_end
    before_start = datetime(2020, 1, 1, tzinfo=UTC)

    with pytest.raises(InvalidFestivalTimeRange):
        await interactor(UpdateAppSettingsInput(festival_end=before_start))

    # The rejected write leaves the stored range untouched.
    assert (await settings_gateway.get()).festival_end == original_end


async def test_limits_only_change_does_not_broadcast(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(UpdateSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(settings_editor)

    await interactor(UpdateAppSettingsInput(announcement_timeout=42))

    # Persisted, but limits are not in GET /config, so nothing should broadcast —
    # a refetch would return identical public config.
    assert (await settings_gateway.get()).limits.announcement_timeout == 42
    assert realtime.published == []
