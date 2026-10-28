from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.voting.set_voting_time_range import (
    SetVotingTimeRangeInput,
)

pytestmark = pytest.mark.unit


def test_voting_boundaries_require_an_offset() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SetVotingTimeRangeInput(
            voting_starts_at=datetime(2026, 8, 22, 12, 0),  # noqa: DTZ001
            voting_ends_at=datetime(2026, 8, 22, 18, 0),  # noqa: DTZ001
        )

    assert {error["loc"] for error in exc_info.value.errors()} == {
        ("voting_starts_at",),
        ("voting_ends_at",),
    }


def test_voting_boundaries_accept_aware_instants() -> None:
    start = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    end = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)

    parsed = SetVotingTimeRangeInput(voting_starts_at=start, voting_ends_at=end)

    assert parsed.voting_starts_at == start
    assert parsed.voting_ends_at == end


def test_voting_range_can_be_cleared_with_nulls() -> None:
    parsed = SetVotingTimeRangeInput(voting_starts_at=None, voting_ends_at=None)

    assert parsed.voting_starts_at is None
    assert parsed.voting_ends_at is None
