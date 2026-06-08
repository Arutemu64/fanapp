import pytest

from fanfan.core.models.app_settings import AppSettings

pytestmark = pytest.mark.unit


def test_voting_is_disabled_by_default():
    settings = AppSettings()

    assert settings.voting_enabled is False


def test_set_voting_enabled_toggles_value():
    settings = AppSettings()

    settings.set_voting_enabled(True)
    assert settings.voting_enabled is True

    settings.set_voting_enabled(False)
    assert settings.voting_enabled is False


def test_announcement_timeout_has_default():
    settings = AppSettings()

    assert settings.limits.announcement_timeout == 10


def test_set_announcement_timeout_updates_value():
    settings = AppSettings()

    settings.limits.set_announcement_timeout(30)

    assert settings.limits.announcement_timeout == 30
