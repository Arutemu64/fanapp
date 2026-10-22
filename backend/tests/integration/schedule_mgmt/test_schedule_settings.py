from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.schedule_mgmt.schedule_settings import (
    GetScheduleSettings,
    ScheduleSettingsDTO,
    UpdateScheduleSettings,
    UpdateScheduleSettingsInput,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from tests.fakes.realtime_gateway import FakeRealtimeGateway

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_changeover_change_broadcasts_config_updated(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UpdateScheduleSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(schedule_editor)

    await interactor(
        UpdateScheduleSettingsInput(announcement_timeout=20, changeover_seconds=45)
    )

    settings = await settings_gateway.get()
    assert settings.limits.announcement_timeout == 20
    assert settings.schedule.changeover_seconds == 45
    # The changeover is in GET /config, so every open schedule refetches it.
    assert [
        (user_id, message.event_name) for user_id, message in realtime.published
    ] == [(None, SSEEventName.CONFIG_UPDATED)]


async def test_cooldown_only_change_does_not_broadcast(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UpdateScheduleSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(schedule_editor)
    changeover = (await settings_gateway.get()).schedule.changeover_seconds

    await interactor(UpdateScheduleSettingsInput(announcement_timeout=42))

    # Persisted, the omitted changeover left as is, and the cooldown is not in
    # GET /config, so nothing should broadcast — a refetch would return
    # identical public config.
    settings = await settings_gateway.get()
    assert settings.limits.announcement_timeout == 42
    assert settings.schedule.changeover_seconds == changeover
    assert realtime.published == []


async def test_reads_the_stored_settings(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    setter = await dishka_request.get(UpdateScheduleSettings)
    getter = await dishka_request.get(GetScheduleSettings)
    login(schedule_editor)

    await setter(
        UpdateScheduleSettingsInput(announcement_timeout=15, changeover_seconds=60)
    )

    assert await getter() == ScheduleSettingsDTO(
        announcement_timeout=15, changeover_seconds=60
    )


async def test_settings_editor_without_schedule_setup_is_denied(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
) -> None:
    getter = await dishka_request.get(GetScheduleSettings)
    setter = await dishka_request.get(UpdateScheduleSettings)
    login(settings_editor)

    with pytest.raises(AccessDenied):
        await getter()
    with pytest.raises(AccessDenied):
        await setter(UpdateScheduleSettingsInput(announcement_timeout=10))
