import pytest

from fanfan.core.exceptions.schedule import (
    CurrentScheduleItemNotAllowed,
    SameScheduleItemsAreNotAllowed,
    SkippedScheduleItemNotAllowed,
)
from fanfan.core.models.schedule_item import ScheduleItem
from fanfan.core.vo.schedule_item import generate_schedule_item_id

pytestmark = pytest.mark.unit


def _event(
    number: int,
    order: float,
    *,
    is_current: bool = False,
    is_skipped: bool = False,
) -> ScheduleItem:
    return ScheduleItem(
        id=generate_schedule_item_id(),
        number=number,
        title=f"Событие {number}",
        duration=15,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
        block_title=None,
    )


def test_set_current_on_normal_event():
    event = _event(1, 1)

    event.set_current()

    assert event.is_current is True


def test_set_current_on_skipped_event_raises():
    event = _event(1, 1, is_skipped=True)

    with pytest.raises(SkippedScheduleItemNotAllowed):
        event.set_current()


def test_skip_on_current_event_raises():
    event = _event(1, 1, is_current=True)

    with pytest.raises(CurrentScheduleItemNotAllowed):
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

    with pytest.raises(SameScheduleItemsAreNotAllowed):
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
