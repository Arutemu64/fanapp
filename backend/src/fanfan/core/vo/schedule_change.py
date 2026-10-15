import enum
from typing import NewType
from uuid import UUID, uuid7

ScheduleChangeId = NewType("ScheduleChangeId", UUID)


def generate_schedule_change_id() -> ScheduleChangeId:
    return ScheduleChangeId(uuid7())


class ScheduleChangeType(enum.StrEnum):
    """How to read a `ScheduleChange`'s `changed_event_id`/`related_entry_id`.

    SET_AS_CURRENT: `changed_event_id` is the new current event (None if the
        current event was unchecked); `related_entry_id` is the event that was
        current before this change.
    MOVED: `related_entry_id` is the entry `changed_event_id` sat right after
        before the move — a block start when the event opened its block. To
        undo, place `changed_event_id` back after `related_entry_id` — or at
        the top of the order if `related_entry_id` is None.
    SKIPPED / UNSKIPPED: `related_entry_id` is unused.
    """

    SET_AS_CURRENT = "set_as_current"
    MOVED = "moved"
    SKIPPED = "skipped"
    UNSKIPPED = "unskipped"
