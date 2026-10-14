from pydantic import BaseModel

from fanfan.core.vo.schedule_entry import ScheduleEntryId


class MoveScheduleEventRequest(BaseModel):
    place_after_event_id: ScheduleEntryId


class UpdateScheduleEventRequest(BaseModel):
    is_skipped: bool
