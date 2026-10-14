from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_entry import ScheduleEntryId, ScheduleEntryType
from fanfan.core.vo.user import UserId


class ScheduleChangeEntryDTO(BaseModel):
    id: ScheduleEntryId
    # A move records the entry the event sat right after before it moved,
    # which is a block start when the event opened its block.
    type: ScheduleEntryType
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
    changed_event: ScheduleChangeEntryDTO | None
    related_entry: ScheduleChangeEntryDTO | None
    user: ScheduleChangeUserDTO | None
    created_at: datetime
