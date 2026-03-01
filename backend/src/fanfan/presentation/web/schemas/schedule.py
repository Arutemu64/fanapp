from pydantic import BaseModel

from fanfan.core.vo.schedule_event import ScheduleEventId


class MoveScheduleEventRequest(BaseModel):
    place_after_event_id: ScheduleEventId
