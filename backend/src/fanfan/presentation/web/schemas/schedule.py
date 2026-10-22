from pydantic import BaseModel

from fanfan.core.vo.schedule_entry import ScheduleEntryId


class MoveScheduleEventBody(BaseModel):
    place_after_entry_id: ScheduleEntryId


class UpdateScheduleEventBody(BaseModel):
    is_skipped: bool
