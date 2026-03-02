from dataclasses import dataclass

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class ScheduleChange:
    id: ScheduleChangeId
    type: ScheduleChangeType

    # Arguments
    changed_event_id: ScheduleEventId | None
    argument_event_id: ScheduleEventId | None

    # Mailing
    mailing_id: MailingId | None
    user_id: UserId | None
    send_global_announcement: bool
