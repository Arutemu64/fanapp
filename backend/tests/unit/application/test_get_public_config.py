from datetime import UTC, datetime

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


async def test_projects_public_fields_from_settings() -> None:
    start = datetime(2026, 8, 22, 11, 30, tzinfo=UTC)
    end = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)
    voting_starts_at = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    voting_ends_at = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings = AppSettings(
        voting_starts_at=voting_starts_at,
        voting_ends_at=voting_ends_at,
        festival_starts_at=start,
        festival_ends_at=end,
    )

    result = await GetPublicConfig(_FakeAppSettingsGateway(settings))()

    assert result.festival_starts_at == start
    assert result.festival_ends_at == end
    assert not hasattr(result, "limits")
    assert not hasattr(result, "voting_starts_at")
    assert not hasattr(result, "voting_ends_at")


async def test_projects_the_quest_switch() -> None:
    settings = AppSettings()
    settings.update_quest(enabled=True)

    result = await GetPublicConfig(_FakeAppSettingsGateway(settings))()

    assert result.quest_enabled is True


async def test_projects_the_changeover() -> None:
    settings = AppSettings()
    settings.update_schedule(changeover_seconds=45)

    result = await GetPublicConfig(_FakeAppSettingsGateway(settings))()

    assert result.schedule_changeover_seconds == 45
