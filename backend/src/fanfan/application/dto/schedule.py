from typing import Annotated, Literal

from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryType


class ScheduleEventFullDTO(BaseModel):
    type: Literal[ScheduleEntryType.EVENT]
    id: ScheduleEntryId
    number: int | None
    title: str
    duration: int
    order: float
    is_current: bool
    is_skipped: bool
    nomination_title: str | None

    position: int | None


class ScheduleBlockStartDTO(BaseModel):
    type: Literal[ScheduleEntryType.BLOCK_START]
    id: ScheduleEntryId
    title: str
    order: float


type ScheduleEntryDTO = Annotated[
    ScheduleEventFullDTO | ScheduleBlockStartDTO, Field(discriminator="type")
]
