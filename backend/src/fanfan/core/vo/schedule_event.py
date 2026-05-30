from __future__ import annotations

from typing import NewType
from uuid import UUID, uuid7

ScheduleEventId = NewType("ScheduleEventId", UUID)
ScheduleEventPublicNumber = NewType("ScheduleEventPublicNumber", int)


def generate_schedule_event_id() -> ScheduleEventId:
    return ScheduleEventId(uuid7())
