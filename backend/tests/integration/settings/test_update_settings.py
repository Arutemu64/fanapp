from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName
from fanfan.application.interactors.settings.get_settings import GetSettings
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
    UpdateSettings,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.settings import (
    AppSettingsChanged,
    InvalidFestivalTimeRange,
)
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

    # Derived from the shipped default so it stays after the default start and
    # differs from the stored end whichever year the defaults are moved to.
    new_end = DEFAULT_FESTIVAL_END + timedelta(hours=1)
    await interactor(UpdateAppSettingsInput(festival_end=new_end), if_match=None)

    assert (await settings_gateway.get()).festival_end == new_end
    # A single broadcast (user_id=None) so every open home page refetches /config.
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

    # Partial update touching only the end: it must be validated against the
    # persisted start, not accepted in isolation.
    original_end = (await settings_gateway.get()).festival_end
    before_start = datetime(2020, 1, 1, tzinfo=UTC)

    with pytest.raises(InvalidFestivalTimeRange):
        await interactor(
            UpdateAppSettingsInput(festival_end=before_start), if_match=None
        )

    # The rejected write leaves the stored range untouched.
    assert (await settings_gateway.get()).festival_end == original_end


async def test_save_against_a_stale_etag_is_refused(
    dishka_request: AsyncContainer,
    settings_editor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(UpdateSettings)
    getter = await dishka_request.get(GetSettings)
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    login(settings_editor)

    # Two organizers open the form on the same version; the first one saves.
    read_by_both = (await getter()).etag
    first_save = await interactor(
        UpdateAppSettingsInput.model_validate({"quest": {"max_award": 7}}),
        if_match=frozenset({read_by_both}),
    )
    assert first_save.etag != read_by_both

    # The second save still carries the version both read, so it must not
    # overwrite the first organizer's change.
    with pytest.raises(AppSettingsChanged):
        await interactor(
            UpdateAppSettingsInput.model_validate({"quest": {"max_award": 3}}),
            if_match=frozenset({read_by_both}),
        )

    assert (await settings_gateway.get()).quest.max_award == 7
