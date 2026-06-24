import enum
from typing import NewType
from uuid import UUID, uuid7

ScheduleChangeId = NewType("ScheduleChangeId", UUID)


def generate_schedule_change_id() -> ScheduleChangeId:
    return ScheduleChangeId(uuid7())


class ScheduleChangeType(enum.StrEnum):
    SET_AS_CURRENT = "set_as_current"
    # Changed schedule item: the new current item (None if current was unchecked)
    # Argument schedule item: previously current item

    MOVED = "moved"
    # Argument schedule item: previous item by order before moving
    # So if you want to undo this change, you should place
    # changed_schedule_item AFTER argument_schedule_item
    # And if argument_schedule_item is None - place changed_schedule_item to the top

    SKIPPED = "skipped"
    # Argument schedule item: None

    UNSKIPPED = "unskipped"
    # Argument schedule item: None
