from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from fanfan.core.vo.schedule_entry import ScheduleEntryId


class SetCurrentScheduleEventBody(BaseModel):
    event_id: ScheduleEntryId


class UpdateScheduleEventBody(BaseModel):
    """One change per request: each is its own announcement and undo step."""

    # The field present picks the action, so a misspelt one must not fall through.
    model_config = ConfigDict(extra="forbid")

    # SkipJsonSchema keeps the spec at a plain boolean; null is still refused below.
    is_skipped: bool | SkipJsonSchema[None] = None
    place_after_entry_id: ScheduleEntryId | None = Field(
        default=None,
        description="Entry to place the event after. Null moves it to the top.",
    )

    @model_validator(mode="after")
    def _one_change(self) -> Self:
        if len(self.model_fields_set) != 1:
            msg = "Send exactly one of is_skipped or place_after_entry_id"
            raise ValueError(msg)
        if "is_skipped" in self.model_fields_set and self.is_skipped is None:
            msg = "is_skipped must be true or false"
            raise ValueError(msg)
        return self
