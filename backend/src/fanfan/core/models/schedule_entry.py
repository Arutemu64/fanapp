from dataclasses import dataclass

from fanfan.core.exceptions.schedule import (
    BlockStartNotAllowed,
    CurrentEventNotAllowed,
    SameEventsAreNotAllowed,
    SkippedEventNotAllowed,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryKind


@dataclass(slots=True, kw_only=True)
class ScheduleEntry(AggregateRoot):
    id: ScheduleEntryId
    kind: ScheduleEntryKind
    # The public number printed in the programme. Optional because not every row
    # on stage gets one — breaks and other filler are announced by title alone.
    number: int | None
    title: str
    # Planned stage time in seconds. Seconds rather than minutes because acts
    # shorter than a minute are real, and rounding a per-event duration would
    # accumulate error across the programme.
    duration: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None

    @classmethod
    def block_start(
        cls, *, entry_id: ScheduleEntryId, title: str, order: float
    ) -> ScheduleEntry:
        # A block start only marks where a block begins: nothing happens on
        # stage, so it takes no number, time, queue position or stage state.
        return cls(
            id=entry_id,
            kind=ScheduleEntryKind.BLOCK_START,
            number=None,
            title=title,
            duration=0,
            order=order,
            is_current=False,
            is_skipped=False,
            nomination_title=None,
        )

    def _ensure_event(self) -> None:
        if self.kind is not ScheduleEntryKind.EVENT:
            raise BlockStartNotAllowed

    def set_current(self) -> None:
        self._ensure_event()
        # A skipped event cannot be announced as currently on stage.
        if self.is_skipped:
            raise SkippedEventNotAllowed
        self.is_current = True

    def unset_current(self) -> None:
        self.is_current = False

    def skip(self) -> None:
        self._ensure_event()
        # The current stage event must be unset before it can be skipped.
        if self.is_current:
            raise CurrentEventNotAllowed
        self.is_skipped = True

    def unskip(self) -> None:
        self.is_skipped = False

    def place_after(
        self,
        previous_event: ScheduleEntry,
        next_event: ScheduleEntry | None,
    ) -> None:
        # Only events move. A block start stays put, and moving an event across
        # one is what carries the event into another block.
        self._ensure_event()
        if self == previous_event:
            raise SameEventsAreNotAllowed
        self.order = (
            (previous_event.order + next_event.order) / 2
            if next_event
            else previous_event.order + 1
        )

    def place_before_first(self, first_event: ScheduleEntry | None) -> None:
        self._ensure_event()
        self.order = first_event.order - 1 if first_event else 1

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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ScheduleEntry) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
