from typing import NewType
from uuid import UUID, uuid7

ScheduleEventId = NewType("ScheduleEventId", UUID)


def generate_schedule_event_id() -> ScheduleEventId:
    return ScheduleEventId(uuid7())
