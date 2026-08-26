from datetime import UTC, datetime, timedelta, timezone

import pytest

from fanfan.core.exceptions.settings import InvalidVotingTimeRange
from fanfan.core.models.app_settings import (
    DEFAULT_FESTIVAL_END,
    DEFAULT_FESTIVAL_START,
    AppSettings,
)

pytestmark = pytest.mark.unit


def test_voting_is_closed_by_default():
    settings = AppSettings()

    assert settings.voting_start is None
    assert settings.voting_end is None
    assert settings.is_voting_open(now=datetime.now(UTC)) is False


def test_festival_defaults():
    settings = AppSettings()

    assert settings.festival_start == DEFAULT_FESTIVAL_START
    assert settings.festival_end == DEFAULT_FESTIVAL_END


def test_set_festival_start_updates_value():
    settings = AppSettings()
    new_start = datetime(2027, 8, 21, 10, 0, tzinfo=UTC)

    settings.set_festival_start(start=new_start)

    assert settings.festival_start == new_start


def test_set_festival_end_updates_value():
    settings = AppSettings()
    new_end = datetime(2027, 8, 22, 20, 0, tzinfo=UTC)

    settings.set_festival_end(end=new_end)

    assert settings.festival_end == new_end


def test_set_voting_time_range_updates_values():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)

    settings.set_voting_time_range(start=start, end=end)

    assert settings.voting_start == start
    assert settings.voting_end == end


def test_is_voting_open_inside_range():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings.set_voting_time_range(start=start, end=end)

    assert settings.is_voting_open(now=datetime(2026, 8, 22, 15, 0, tzinfo=UTC)) is True


def test_is_voting_open_at_start_boundary():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings.set_voting_time_range(start=start, end=end)

    assert settings.is_voting_open(now=start) is True


def test_is_voting_closed_at_end_boundary():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings.set_voting_time_range(start=start, end=end)

    assert settings.is_voting_open(now=end) is False


def test_is_voting_closed_before_range():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    settings.set_voting_time_range(start=start, end=end)

    assert (
        settings.is_voting_open(now=datetime(2026, 8, 22, 11, 0, tzinfo=UTC)) is False
    )


def test_is_voting_closed_when_range_cleared():
    settings = AppSettings()
    settings.set_voting_time_range(start=None, end=None)

    assert settings.is_voting_open(now=datetime.now(UTC)) is False


def test_set_voting_time_range_rejects_reversed_range():
    settings = AppSettings()
    start = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)

    with pytest.raises(InvalidVotingTimeRange):
        settings.set_voting_time_range(start=start, end=end)


def test_set_voting_time_range_rejects_zero_length():
    settings = AppSettings()
    point = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)

    with pytest.raises(InvalidVotingTimeRange):
        settings.set_voting_time_range(start=point, end=point)


def test_set_voting_time_range_rejects_partial_start_only():
    settings = AppSettings()

    with pytest.raises(InvalidVotingTimeRange):
        settings.set_voting_time_range(
            start=datetime(2026, 8, 22, 12, 0, tzinfo=UTC), end=None
        )


def test_set_voting_time_range_rejects_partial_end_only():
    settings = AppSettings()

    with pytest.raises(InvalidVotingTimeRange):
        settings.set_voting_time_range(
            start=None, end=datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
        )


def test_announcement_timeout_has_default():
    settings = AppSettings()

    assert settings.limits.announcement_timeout == 10


def test_update_limits_updates_announcement_timeout():
    settings = AppSettings()

    settings.update_limits(announcement_timeout=30)

    assert settings.limits.announcement_timeout == 30
