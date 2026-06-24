from typing import NewType
from uuid import UUID, uuid7

ScheduleItemId = NewType("ScheduleItemId", UUID)


def generate_schedule_item_id() -> ScheduleItemId:
    return ScheduleItemId(uuid7())
