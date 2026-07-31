from datetime import UTC, datetime, timedelta

import pytest

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.services.schedule_timing import project_seconds_until
from fanfan.core.vo.schedule_event import generate_schedule_event_id

pytestmark = pytest.mark.unit

ANCHOR = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
BUFFER = 60


def _event(
    number: int,
    order: float,
    *,
    duration_seconds: int = 600,
    is_current: bool = False,
    is_skipped: bool = False,
    actual_start_time: datetime | None = None,
) -> ScheduleEventFullDTO:
    return ScheduleEventFullDTO(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=duration_seconds,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
        block_title=None,
        actual_start_time=actual_start_time,
        queue=number,
    )


def test_no_current_event_reports_no_waits():
    events = [_event(1, 1.0), _event(2, 2.0)]

    waits = project_seconds_until(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert waits == {}


def test_current_event_without_anchor_reports_no_waits():
    events = [_event(1, 1.0, is_current=True), _event(2, 2.0)]

    waits = project_seconds_until(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert waits == {}


def test_measures_from_what_is_left_of_the_act_on_stage():
    current = _event(
        1, 1.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    second = _event(2, 2.0, duration_seconds=300)
    third = _event(3, 3.0, duration_seconds=120)
    events = [current, second, third]

    waits = project_seconds_until(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    # Nothing to report for the act already on stage.
    assert current.id not in waits
    # All 600s of the current act still to run, plus the changeover.
    assert waits[second.id] == 660
    # Then the second act's 300s and another changeover.
    assert waits[third.id] == 1020


def test_wait_counts_down_as_the_current_act_runs():
    current = _event(
        1, 1.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    second = _event(2, 2.0, duration_seconds=300)

    waits = project_seconds_until(
        [current, second],
        transition_buffer_seconds=BUFFER,
        # Four minutes into the act, so 360s of it are left.
        now=ANCHOR + timedelta(seconds=240),
    )

    assert waits[second.id] == 420


def test_past_and_skipped_events_get_no_wait():
    past = _event(1, 1.0)
    current = _event(
        2, 2.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    skipped = _event(3, 3.0, duration_seconds=9999, is_skipped=True)
    upcoming = _event(4, 4.0, duration_seconds=300)
    events = [past, current, skipped, upcoming]

    waits = project_seconds_until(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert past.id not in waits
    assert skipped.id not in waits
    # Skipped event consumes no stage time: upcoming still follows current.
    assert waits[upcoming.id] == 660


def test_overrun_never_reports_a_negative_wait():
    current = _event(
        1, 1.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    second = _event(2, 2.0, duration_seconds=300)
    third = _event(3, 3.0, duration_seconds=120)
    events = [current, second, third]

    # Current act has run 30 min though its planned duration was 10 min.
    now = ANCHOR + timedelta(minutes=30)

    waits = project_seconds_until(events, transition_buffer_seconds=BUFFER, now=now)

    # The overrunning act owes no more stage time, but the changeover remains.
    assert waits[second.id] == BUFFER
    # Third follows on from that, not from the original plan.
    assert waits[third.id] == BUFFER + 300 + BUFFER
