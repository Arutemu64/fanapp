from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
    UpdateSettings,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import InvalidFestivalTimeRange
from fanfan.core.models.app_settings import DEFAULT_FESTIVAL_END
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
) -> None:
    interactor = await dishka_request.get(UpdateSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(settings_editor)

    new_end = DEFAULT_FESTIVAL_END + timedelta(hours=1)
    await interactor(UpdateAppSettingsInput(festival_end=new_end))

    assert (await settings_gateway.get()).festival_end == new_end
    assert [
        (user_id, message.event_name) for user_id, message in realtime.published
    ] == [(None, SSEEventName.CONFIG_UPDATED)]


async def test_festival_end_before_start_is_rejected(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UpdateSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    login(settings_editor)

    original_end = (await settings_gateway.get()).festival_end
    before_start = datetime(2020, 1, 1, tzinfo=UTC)

    with pytest.raises(InvalidFestivalTimeRange):
        await interactor(UpdateAppSettingsInput(festival_end=before_start))

    assert (await settings_gateway.get()).festival_end == original_end
