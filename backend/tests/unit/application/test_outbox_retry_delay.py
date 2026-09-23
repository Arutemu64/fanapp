from datetime import timedelta

import pytest

from fanfan.application.interactors.outbox.publish_outbox_events import (
    _RETRY_MAX_DELAY,
    _retry_delay,
)

pytestmark = pytest.mark.unit


def test_retry_delay_doubles_from_one_second() -> None:
    delays = [_retry_delay(attempt) for attempt in (1, 2, 3, 4)]
    assert delays == [timedelta(seconds=n) for n in (1, 2, 4, 8)]


def test_retry_delay_is_capped() -> None:
    assert _retry_delay(20) == _RETRY_MAX_DELAY


def test_retry_delay_survives_a_row_failing_for_days() -> None:
    # A row NATS keeps rejecting is retried every few minutes indefinitely; an
    # unclamped exponent would overflow timedelta after a few dozen attempts.
    assert _retry_delay(5000) == _RETRY_MAX_DELAY
