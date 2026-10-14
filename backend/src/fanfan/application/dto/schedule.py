from typing import Annotated, Literal

from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryKind


class ScheduleEventFullDTO(BaseModel):
    kind: Literal[ScheduleEntryKind.EVENT]
    id: ScheduleEntryId
    # None for events with no public number (breaks and other filler rows).
    number: int | None
    title: str
    # Seconds; the API exposes it unconverted so clients can render sub-minute
    # acts exactly instead of rounding to whole minutes.
    duration: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None

    # Calculated value: dense 1..N position among non-skipped events (ADR-0008).
    # Every field on this DTO is now derived purely from stored columns, so the
    # whole schedule read is stable between edits and cacheable (see ADR-0014).
    queue: int | None


class ScheduleBlockStartDTO(BaseModel):
    kind: Literal[ScheduleEntryKind.BLOCK_START]
    id: ScheduleEntryId
    title: str
    order: float


# Flat, in programme order, rather than events nested under their block: a
# block is just the run of entries after its start, so the list is the one
# shape that moving an event between blocks never has to restructure.
type ScheduleEntryDTO = Annotated[
    ScheduleEventFullDTO | ScheduleBlockStartDTO, Field(discriminator="kind")
]
