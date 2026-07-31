from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


class ScheduleChangeEventDTO(BaseModel):
    id: ScheduleEventId
    number: int | None
    title: str
    order: float


class ScheduleChangeUserDTO(BaseModel):
    id: UserId
    username: str


class ScheduleChangeFullDTO(BaseModel):
    id: ScheduleChangeId
    type: ScheduleChangeType
    mailing_id: MailingId | None
    user_id: UserId | None
    next_event_changed: bool
    changed_event: ScheduleChangeEventDTO | None
    argument_event: ScheduleChangeEventDTO | None
    user: ScheduleChangeUserDTO | None
