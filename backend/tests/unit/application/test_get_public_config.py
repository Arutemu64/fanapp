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
    assert result.voting_enabled is True
    # limits is organizer-only and must not leak into the public projection.
    assert not hasattr(result, "limits")
