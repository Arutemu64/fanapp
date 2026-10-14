import enum
from typing import NewType
from uuid import UUID, uuid7

ScheduleEntryId = NewType("ScheduleEntryId", UUID)


def generate_schedule_entry_id() -> ScheduleEntryId:
    return ScheduleEntryId(uuid7())


class ScheduleEntryKind(enum.StrEnum):
    """What a row of the programme is.

    EVENT: something that happens on stage — an act, a break, the opening.
    BLOCK_START: the heading of a programme block. Every entry after it, up to
        the next block start, belongs to that block, so moving an event across
        a block start moves it into the other block.
    """

    EVENT = "event"
    BLOCK_START = "block_start"
