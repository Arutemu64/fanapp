from datetime import UTC, datetime, timedelta

import pytest
from procrastinate.jobs import Job

from fanfan.core.exceptions.notifications import NotificationRetryAfter
from fanfan.presentation.worker.retry import MAX_ATTEMPTS, BoundedBackoff

pytestmark = pytest.mark.unit


def _job(attempts: int) -> Job:
    return Job(
        queue="default",
        lock=None,
        queueing_lock=None,
        task_name="probe",
        attempts=attempts,
    )


def _delay_seconds(exception: BaseException, attempts: int) -> float | None:
    before = datetime.now(UTC)
    decision = BoundedBackoff().get_retry_decision(
        exception=exception, job=_job(attempts)
    )
    if decision is None:
        return None
    assert decision.retry_at is not None
    return round((decision.retry_at - before).total_seconds())


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [(0, 1), (1, 5), (2, 30), (3, 120), (4, 300), (10, 300)],
)
def test_delay_grows_then_caps(attempts: int, expected: int) -> None:
    assert _delay_seconds(RuntimeError(), attempts) == expected


def test_gives_up_after_max_attempts() -> None:
    # attempts counts the runs before this one, so this run is the last.
    assert _delay_seconds(RuntimeError(), MAX_ATTEMPTS - 1) is None
    assert _delay_seconds(RuntimeError(), MAX_ATTEMPTS - 2) is not None


def test_flood_control_waits_the_delay_the_channel_asked_for() -> None:
    assert _delay_seconds(NotificationRetryAfter(retry_after=42), 0) == 42


def test_flood_control_still_counts_towards_the_limit() -> None:
    exception = NotificationRetryAfter(retry_after=42)
    assert _delay_seconds(exception, MAX_ATTEMPTS - 1) is None


def test_retry_at_is_timezone_aware() -> None:
    decision = BoundedBackoff().get_retry_decision(
        exception=RuntimeError(), job=_job(0)
    )
    assert decision is not None
    assert decision.retry_at is not None
    assert decision.retry_at.utcoffset() == timedelta(0)
