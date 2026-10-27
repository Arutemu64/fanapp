from datetime import datetime

from pydantic import BaseModel

from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryType


class ScheduleChangeEntryDTO(BaseModel):
    id: ScheduleEntryId
    type: ScheduleEntryType
    number: int | None
    title: str


class ScheduleChangeFullDTO(BaseModel):
    id: ScheduleChangeId
    type: ScheduleChangeType
    mailing_id: MailingId | None
    next_event_changed: bool
    changed_event: ScheduleChangeEntryDTO | None
    related_entry: ScheduleChangeEntryDTO | None
    user: UserRefDTO | None
    created_at: datetime
