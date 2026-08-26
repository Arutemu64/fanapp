from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.voting.set_voting_time_range import (
    SetVotingTimeRangeInput,
)

pytestmark = pytest.mark.unit


def test_voting_boundaries_require_an_offset():
    # A naive bound must be rejected here: once persisted it is compared against an
    # aware clock in AppSettings.is_voting_open(now), which would raise TypeError
    # on every voting-status check.
    with pytest.raises(ValidationError):
        SetVotingTimeRangeInput(
            voting_start=datetime(2026, 8, 22, 12, 0),  # noqa: DTZ001
            voting_end=datetime(2026, 8, 22, 18, 0),  # noqa: DTZ001
        )


def test_voting_boundaries_accept_aware_instants():
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)

    parsed = SetVotingTimeRangeInput(voting_start=start, voting_end=end)

    assert parsed.voting_start == start
    assert parsed.voting_end == end


def test_voting_range_can_be_cleared_with_nulls():
    # Closing the vote sends both bounds null; that must stay valid.
    parsed = SetVotingTimeRangeInput(voting_start=None, voting_end=None)

    assert parsed.voting_start is None
    assert parsed.voting_end is None
