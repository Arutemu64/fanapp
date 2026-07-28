import enum
from typing import NewType
from uuid import UUID, uuid7

ScheduleChangeId = NewType("ScheduleChangeId", UUID)


def generate_schedule_change_id() -> ScheduleChangeId:
    return ScheduleChangeId(uuid7())


class ScheduleChangeType(enum.StrEnum):
    """How to read a `ScheduleChange`'s `changed_event_id`/`argument_event_id`.

    SET_AS_CURRENT: `changed_event_id` is the new current event (None if the
        current event was unchecked); `argument_event_id` is the event that was
        current before this change.
    MOVED: `argument_event_id` is the event `changed_event_id` was placed
        after. To undo, place `changed_event_id` back after
        `argument_event_id` — or at the top of the order if
        `argument_event_id` is None.
    SKIPPED / UNSKIPPED: `argument_event_id` is unused.
    """

    SET_AS_CURRENT = "set_as_current"
    MOVED = "moved"
    SKIPPED = "skipped"
    UNSKIPPED = "unskipped"
