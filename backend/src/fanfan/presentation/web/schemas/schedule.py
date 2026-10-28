from typing import Self

from pydantic import MISSING, Field, model_validator

from fanfan.application.dto.input import InputModel
from fanfan.core.vo.schedule_entry import ScheduleEntryId


class SetCurrentScheduleEventBody(InputModel):
    event_id: ScheduleEntryId


class UpdateScheduleEventBody(InputModel):
    """One change per request: each is its own announcement and undo step."""

    is_skipped: bool | MISSING = MISSING
    place_after_entry_id: ScheduleEntryId | MISSING | None = Field(
        default=MISSING,
        description="Entry to place the event after. Null moves it to the top.",
    )

    @model_validator(mode="after")
    def _one_change(self) -> Self:
        if len(self.model_fields_set) != 1:
            msg = "Send exactly one of is_skipped or place_after_entry_id"
            raise ValueError(msg)
        return self
