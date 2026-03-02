from __future__ import annotations

from typing import NewType
from uuid import UUID

ScheduleEventId = NewType("ScheduleEventId", UUID)
ScheduleEventPublicNumber = NewType("ScheduleEventPublicNumber", int)
