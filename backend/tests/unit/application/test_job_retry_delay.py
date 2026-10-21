from datetime import timedelta

import pytest

from fanfan.application.services.job_queue import retry_delay

pytestmark = pytest.mark.unit


def test_retry_delay_grows_with_attempts() -> None:
    delays = [retry_delay(attempt) for attempt in (1, 2, 3, 4)]
    assert delays == [
        timedelta(seconds=1),
        timedelta(seconds=5),
        timedelta(seconds=30),
        timedelta(minutes=2),
    ]


def test_retry_delay_repeats_its_last_step() -> None:
    assert retry_delay(5) == timedelta(minutes=5)
    assert retry_delay(500) == timedelta(minutes=5)
