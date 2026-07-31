from datetime import UTC, datetime, timedelta

import pytest

from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    SameEventsAreNotAllowed,
    SkippedEventNotAllowed,
)
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.schedule_event import generate_schedule_event_id

pytestmark = pytest.mark.unit


def _event(
    number: int,
    order: float,
    *,
    is_current: bool = False,
    is_skipped: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=15,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
        block_title=None,
    )


def test_set_current_on_normal_event():
    event = _event(1, 1)
    now = datetime.now(UTC)

    event.set_current(now=now)

    assert event.is_current is True
    assert event.actual_start_time == now


def test_set_current_on_skipped_event_raises():
    event = _event(1, 1, is_skipped=True)

    with pytest.raises(SkippedEventNotAllowed):
        event.set_current(now=datetime.now(UTC))


def test_set_current_preserves_anchor_when_already_current():
    # Re-marking an already-current event must not overwrite the real anchor
    # with a later timestamp.
    event = _event(1, 1)
    first = datetime.now(UTC)
    event.set_current(now=first)

    event.set_current(now=first + timedelta(minutes=5))

    assert event.actual_start_time == first


def test_skip_on_current_event_raises():
    event = _event(1, 1, is_current=True)

    with pytest.raises(CurrentEventNotAllowed):
        event.skip()


def test_skip_then_unskip():
    event = _event(1, 1)

    event.skip()
    assert event.is_skipped is True

    event.unskip()
    assert event.is_skipped is False


def test_place_after_uses_midpoint_when_next_exists():
    event = _event(3, 99)
    previous_event = _event(1, 2)
    next_event = _event(2, 4)

    event.place_after(previous_event, next_event)

    assert event.order == 3  # (2 + 4) / 2


def test_place_after_appends_when_no_next():
    event = _event(3, 99)
    previous_event = _event(1, 2)

    event.place_after(previous_event, None)

    assert event.order == 3  # 2 + 1


def test_place_after_self_raises():
    event = _event(1, 1)

    with pytest.raises(SameEventsAreNotAllowed):
        event.place_after(event, None)


def test_place_before_first_with_existing_first():
    event = _event(2, 99)
    first_event = _event(1, 5)

    event.place_before_first(first_event)

    assert event.order == 4  # 5 - 1


def test_place_before_first_when_no_events():
    event = _event(1, 99)

    event.place_before_first(None)

    assert event.order == 1
