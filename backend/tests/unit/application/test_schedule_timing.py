from datetime import UTC, datetime, timedelta

import pytest

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.services.schedule_timing import apply_expected_start_times
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


def test_no_current_event_leaves_all_projections_none():
    events = [_event(1, 1.0), _event(2, 2.0)]

    apply_expected_start_times(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert all(e.expected_start_time is None for e in events)


def test_projects_forward_from_anchor_with_buffer():
    current = _event(
        1, 1.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    second = _event(2, 2.0, duration_seconds=300)
    third = _event(3, 3.0, duration_seconds=120)
    events = [current, second, third]

    # now is right at the anchor, so nothing is overdue and no clamping happens.
    apply_expected_start_times(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert current.expected_start_time == ANCHOR
    # Second event starts after the current act's 600s plus the 60s buffer.
    assert second.expected_start_time == ANCHOR + timedelta(seconds=660)
    # Third then adds the second act's 300s plus another 60s buffer.
    assert third.expected_start_time == ANCHOR + timedelta(seconds=1020)


def test_past_and_skipped_events_get_no_projection():
    past = _event(1, 1.0)
    current = _event(
        2, 2.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    skipped = _event(3, 3.0, duration_seconds=9999, is_skipped=True)
    upcoming = _event(4, 4.0, duration_seconds=300)
    events = [past, current, skipped, upcoming]

    apply_expected_start_times(events, transition_buffer_seconds=BUFFER, now=ANCHOR)

    assert past.expected_start_time is None
    assert skipped.expected_start_time is None
    # Skipped event consumes no stage time: upcoming still anchors off current.
    assert upcoming.expected_start_time == ANCHOR + timedelta(seconds=660)


def test_overrun_clamps_next_event_to_now_plus_buffer_and_cascades():
    current = _event(
        1, 1.0, duration_seconds=600, is_current=True, actual_start_time=ANCHOR
    )
    second = _event(2, 2.0, duration_seconds=300)
    third = _event(3, 3.0, duration_seconds=120)
    events = [current, second, third]

    # Current act has run 30 min though its planned duration was 10 min.
    now = ANCHOR + timedelta(minutes=30)

    apply_expected_start_times(events, transition_buffer_seconds=BUFFER, now=now)

    # Raw projection for second (anchor + 660s) is in the past, so it floors to
    # now + buffer: even if the overrunning act ended this instant, the
    # transition would still take the buffer.
    assert second.expected_start_time == now + timedelta(seconds=BUFFER)
    # Third then cascades from the clamped value, not the stale raw anchor.
    assert third.expected_start_time == now + timedelta(seconds=BUFFER + 300 + BUFFER)
