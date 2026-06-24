from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.user import UserId


class ScheduleChangeScheduleItemDTO(BaseModel):
    id: ScheduleItemId
    number: int
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
    changed_schedule_item: ScheduleChangeScheduleItemDTO | None
    argument_schedule_item: ScheduleChangeScheduleItemDTO | None
    user: ScheduleChangeUserDTO | None
