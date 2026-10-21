from typing import ClassVar

from fanfan.core.events.base import DomainEvent
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeCreated(DomainEvent):
    subject: ClassVar[str] = "schedule.change.created"

    schedule_change_id: ScheduleChangeId


class ScheduleChangeUndone(DomainEvent):
    subject: ClassVar[str] = "schedule.change.undone"

    mailing_id: MailingId | None
