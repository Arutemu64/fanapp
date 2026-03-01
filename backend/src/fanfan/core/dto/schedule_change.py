from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId, ScheduleEventPublicNumber
from fanfan.core.vo.user import UserId


class ScheduleChangeEventDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ScheduleEventId
    public_number: ScheduleEventPublicNumber
    title: str


class ScheduleChangeUserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str | None


class ScheduleChangeFullDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ScheduleChangeId
    type: ScheduleChangeType
    mailing_id: MailingId | None
    user_id: UserId | None
    send_global_announcement: bool
    changed_event: ScheduleChangeEventDTO | None
    argument_event: ScheduleChangeEventDTO | None
    user: ScheduleChangeUserDTO | None
