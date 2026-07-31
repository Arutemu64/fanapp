from pydantic import BaseModel, Field

from fanfan.core.vo.schedule_event import ScheduleEventId


class MoveScheduleEventRequest(BaseModel):
    # Required but nullable rather than optional: moving an event to the very
    # top is a deliberate choice, so the client says `null` instead of omitting
    # the field and getting the top by accident.
    place_after_event_id: ScheduleEventId | None = Field(
        description="Event to place the moved event behind. "
        "Null moves it to the top of the schedule.",
    )


class UpdateScheduleEventRequest(BaseModel):
    is_skipped: bool
