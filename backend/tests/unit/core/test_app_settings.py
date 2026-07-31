import pytest

from fanfan.core.models.app_settings import AppSettings

pytestmark = pytest.mark.unit


def test_voting_is_disabled_by_default():
    settings = AppSettings()

    assert settings.voting_enabled is False


def test_set_voting_enabled_toggles_value():
    settings = AppSettings()

    settings.set_voting_enabled(enabled=True)
    assert settings.voting_enabled is True

    settings.set_voting_enabled(enabled=False)
    assert settings.voting_enabled is False


def test_announcement_timeout_seconds_has_default():
    settings = AppSettings()

    assert settings.limits.announcement_timeout_seconds == 10


def test_update_limits_updates_announcement_timeout_seconds():
    settings = AppSettings()

    settings.update_limits(announcement_timeout_seconds=30)

    assert settings.limits.announcement_timeout_seconds == 30
