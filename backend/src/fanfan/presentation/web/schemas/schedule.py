from pydantic import BaseModel

from fanfan.core.vo.schedule_item import ScheduleItemId


class MoveScheduleItemRequest(BaseModel):
    place_after_schedule_item_id: ScheduleItemId


class UpdateScheduleItemRequest(BaseModel):
    is_skipped: bool
