from dataclasses import dataclass
from typing import override

from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    SameEventsAreNotAllowed,
    SkippedEventNotAllowed,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_entry import ScheduleEntryId


@dataclass(slots=True, kw_only=True, eq=False)
class BaseScheduleEntry(AggregateRoot):
    """What every row of the programme has: an identity, a title and a place."""

    id: ScheduleEntryId
    title: str
    order: float

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, BaseScheduleEntry) and self.id == other.id

    @override
    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(slots=True, kw_only=True, eq=False)
class ScheduleBlockStart(BaseScheduleEntry):
    """The head of a block: every event after it, up to the next one, is in it.

    Nothing happens on stage here, so it has no number, time, position or
    stage state, and none of the stage operations. It never moves either: moving
    an event across a block start is what carries the event into another block.
    """


@dataclass(slots=True, kw_only=True, eq=False)
class ScheduleEvent(BaseScheduleEntry):
    number: int | None
    duration: int
    is_current: bool
    is_skipped: bool
    nomination_title: str | None

    def set_current(self) -> None:
        if self.is_skipped:
            raise SkippedEventNotAllowed
        self.is_current = True

    def unset_current(self) -> None:
        self.is_current = False

    def skip(self) -> None:
        if self.is_current:
            raise CurrentEventNotAllowed
        self.is_skipped = True

    def unskip(self) -> None:
        self.is_skipped = False

    def place_after(
        self,
        previous_entry: ScheduleEntry,
        next_entry: ScheduleEntry | None,
    ) -> None:
        if self == previous_entry:
            raise SameEventsAreNotAllowed
        self.order = (
            (previous_entry.order + next_entry.order) / 2
            if next_entry
            else previous_entry.order + 1
        )

    def place_before_first(self, first_entry: ScheduleEntry | None) -> None:
        self.order = first_entry.order - 1 if first_entry else 1

    def update_details(
        self,
        *,
        title: str,
        duration: int,
        nomination_title: str | None,
        order: float,
    ) -> None:
        self.title = title
        self.duration = duration
        self.nomination_title = nomination_title
        self.order = order


type ScheduleEntry = ScheduleEvent | ScheduleBlockStart
