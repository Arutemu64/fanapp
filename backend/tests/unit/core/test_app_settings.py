from datetime import UTC, datetime, timezone

import pytest

from fanfan.core.models.app_settings import DEFAULT_FESTIVAL_START, AppSettings

pytestmark = pytest.mark.unit


def test_voting_is_disabled_by_default():
    settings = AppSettings()

    assert settings.voting_enabled is False


def test_festival_defaults():
    settings = AppSettings()

    assert settings.festival_start == DEFAULT_FESTIVAL_START
    assert settings.festival_ended is False


def test_set_festival_start_updates_value():
    settings = AppSettings()
    new_start = datetime(2027, 8, 21, 10, 0, tzinfo=UTC)

    settings.set_festival_start(start=new_start)

    assert settings.festival_start == new_start


def test_set_festival_ended_toggles_value():
    settings = AppSettings()

    settings.set_festival_ended(ended=True)
    assert settings.festival_ended is True

    settings.set_festival_ended(ended=False)
    assert settings.festival_ended is False


def test_set_voting_enabled_toggles_value():
    settings = AppSettings()

    settings.set_voting_enabled(enabled=True)
    assert settings.voting_enabled is True

    settings.set_voting_enabled(enabled=False)
    assert settings.voting_enabled is False


def test_announcement_timeout_has_default():
    settings = AppSettings()

    assert settings.limits.announcement_timeout == 10


def test_update_limits_updates_announcement_timeout():
    settings = AppSettings()

    settings.update_limits(announcement_timeout=30)

    assert settings.limits.announcement_timeout == 30
