import pytest

from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    SameEventsAreNotAllowed,
    SkippedEventNotAllowed,
)
from fanfan.core.models.schedule_entry import ScheduleBlockStart, ScheduleEvent
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id

pytestmark = pytest.mark.unit


def _event(
    number: int,
    order: float,
    *,
    is_current: bool = False,
    is_skipped: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=15,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
    )


def test_set_current_on_normal_event() -> None:
    event = _event(1, 1)

    event.set_current()

    assert event.is_current is True


def test_set_current_on_skipped_event_raises() -> None:
    event = _event(1, 1, is_skipped=True)

    with pytest.raises(SkippedEventNotAllowed):
        event.set_current()


def test_skip_on_current_event_raises() -> None:
    event = _event(1, 1, is_current=True)

    with pytest.raises(CurrentEventNotAllowed):
        event.skip()


def test_skip_then_unskip() -> None:
    event = _event(1, 1)

    event.skip()
    assert event.is_skipped is True

    event.unskip()
    assert event.is_skipped is False


def test_place_after_uses_midpoint_when_next_exists() -> None:
    event = _event(3, 99)
    previous_event = _event(1, 2)
    next_event = _event(2, 4)

    event.place_after(previous_event, next_event)

    assert event.order == 3


def test_place_after_appends_when_no_next() -> None:
    event = _event(3, 99)
    previous_event = _event(1, 2)

    event.place_after(previous_event, None)

    assert event.order == 3


def test_place_after_self_raises() -> None:
    event = _event(1, 1)

    with pytest.raises(SameEventsAreNotAllowed):
        event.place_after(event, None)


def test_place_before_first_with_existing_first() -> None:
    event = _event(2, 99)
    first_event = _event(1, 5)

    event.place_before_first(first_event)

    assert event.order == 4


def test_place_before_first_when_no_events() -> None:
    event = _event(1, 99)

    event.place_before_first(None)

    assert event.order == 1


def _block_start(order: float) -> ScheduleBlockStart:
    return ScheduleBlockStart(
        id=generate_schedule_entry_id(), title="Косплей", order=order
    )


def test_entries_are_equal_by_id_across_kinds() -> None:
    event = _event(1, 1)
    same_event_later = _event(1, 7)
    same_event_later.id = event.id

    assert event == same_event_later
    assert event != _block_start(1)
    assert len({event, same_event_later}) == 1


def test_an_event_moves_after_a_block_start() -> None:
    event = _event(1, 99)

    event.place_after(_block_start(10), _event(2, 20))

    assert event.order == 15
