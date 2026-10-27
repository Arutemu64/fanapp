from typing import Annotated, Literal

from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryType


class ScheduleEventFullDTO(BaseModel):
    type: Literal[ScheduleEntryType.EVENT]
    id: ScheduleEntryId
    number: int | None
    title: str
    duration_seconds: int
    is_skipped: bool
    nomination_title: str | None

    position: int | None


class ScheduleBlockStartDTO(BaseModel):
    type: Literal[ScheduleEntryType.BLOCK_START]
    id: ScheduleEntryId
    title: str


type ScheduleEntryDTO = Annotated[
    ScheduleEventFullDTO | ScheduleBlockStartDTO, Field(discriminator="type")
]


class ScheduleDTO(BaseModel):
    current_event_id: ScheduleEntryId | None
    schedule: list[ScheduleEntryDTO] = Field(
        description="Every entry in running order."
    )
