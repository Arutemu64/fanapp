import enum
from typing import NewType

ScheduleChangeId = NewType("ScheduleChangeId", int)


class ScheduleChangeType(enum.StrEnum):
    SET_AS_CURRENT = "set_as_current"
    # Changed event: current event (None if current event was unchecked)
    # Argument event: previously current event

    MOVED = "moved"
    # Argument event: previous event by order before moving
    # So if you want to undo this change, you should place
    # changed_event AFTER argument event
    # And if argument_event is None - place changed_event to the top

    SKIPPED = "skipped"
    # Argument event: None

    UNSKIPPED = "unskipped"
    # Argument event: None
