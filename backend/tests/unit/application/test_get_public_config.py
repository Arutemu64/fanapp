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
    end = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)
    voting_start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    voting_end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings = AppSettings(
        voting_start=voting_start,
        voting_end=voting_end,
        festival_start=start,
        festival_end=end,
    )

    result = await GetPublicConfig(_FakeAppSettingsGateway(settings))()

    assert result.festival_start == start
    assert result.festival_end == end
    # Neither limits (organizer-only) nor the voting time range leak into the
    # public projection: voting availability is served per-user from
    # GET /voting/status, so the time range must not appear here.
    assert not hasattr(result, "limits")
    assert not hasattr(result, "voting_start")
    assert not hasattr(result, "voting_end")
