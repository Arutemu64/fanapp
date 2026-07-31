from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    SameEventsAreNotAllowed,
    SkippedEventNotAllowed,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_event import ScheduleEventId


@dataclass(slots=True, kw_only=True)
class ScheduleEvent(AggregateRoot):
    id: ScheduleEventId
    number: int
    title: str
    duration_seconds: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None
    block_title: str | None
    # Wall-clock moment the event actually went on stage; the anchor for
    # drift-aware expected-time projection (ADR-0008). None until first set.
    actual_start_time: datetime | None = None

    def set_current(self, now: datetime) -> None:
        # A skipped event cannot be announced as currently on stage.
        if self.is_skipped:
            raise SkippedEventNotAllowed
        # Stamp the real start only on the False->True transition so a repeated
        # call (or re-marking an already-current event) never overwrites the
        # genuine anchor with a later timestamp.
        if not self.is_current:
            self.actual_start_time = now
        self.is_current = True

    def unset_current(self) -> None:
        self.is_current = False

    def skip(self) -> None:
        # The current stage event must be unset before it can be skipped.
        if self.is_current:
            raise CurrentEventNotAllowed
        self.is_skipped = True

    def unskip(self) -> None:
        self.is_skipped = False

    def place_after(
        self,
        previous_event: ScheduleEvent,
        next_event: ScheduleEvent | None,
    ) -> None:
        if self == previous_event:
            raise SameEventsAreNotAllowed
        self.order = (
            (previous_event.order + next_event.order) / 2
            if next_event
            else previous_event.order + 1
        )

    def place_before_first(self, first_event: ScheduleEvent | None) -> None:
        self.order = first_event.order - 1 if first_event else 1

    def update_details(
        self,
        *,
        title: str,
        duration_seconds: int,
        block_title: str | None,
        nomination_title: str | None,
        order: float,
    ) -> None:
        self.title = title
        self.duration_seconds = duration_seconds
        self.block_title = block_title
        self.nomination_title = nomination_title
        self.order = order

    def __eq__(self, other: ScheduleEvent | Any) -> bool:
        return isinstance(other, ScheduleEvent) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
