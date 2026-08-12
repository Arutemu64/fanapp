from datetime import UTC, datetime, timezone

import pytest

from fanfan.application.interactors.settings.get_public_config import GetPublicConfig
from fanfan.core.models.app_settings import AppSettings

pytestmark = pytest.mark.unit


class _FakeAppSettingsGateway:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def get(self) -> AppSettings:
        return self._settings

    async def get_for_update(self) -> AppSettings:
        return self._settings

    async def save(self, settings: AppSettings) -> None:
        self._settings = settings


async def test_projects_public_fields_from_settings():
    start = datetime(2026, 8, 22, 11, 30, tzinfo=UTC)
    settings = AppSettings(
        voting_enabled=True, festival_start=start, festival_ended=True
    )

    result = await GetPublicConfig(_FakeAppSettingsGateway(settings))()

    assert result.festival_start == start
    assert result.festival_ended is True
    # Neither limits (organizer-only) nor voting_enabled leak into the public
    # projection: voting availability is served per-user from GET /voting/status,
    # so the enabled input above must not appear here.
    assert not hasattr(result, "limits")
    assert not hasattr(result, "voting_enabled")
