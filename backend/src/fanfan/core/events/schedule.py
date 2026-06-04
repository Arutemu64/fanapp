from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId


class ScheduleChangeCreated(AppEvent):
    subject: ClassVar[str] = "schedule.change.created"

    schedule_change_id: ScheduleChangeId


class ScheduleChangeUndone(AppEvent):
    subject: ClassVar[str] = "schedule.change.undone"

    mailing_id: MailingId | None
