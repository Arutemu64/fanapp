from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId

REMINDER_POSITIONS_AHEAD = 2


@dataclass(slots=True, kw_only=True)
class Subscription(AggregateRoot):
    id: SubscriptionId
    user_id: UserId
    event_id: ScheduleEntryId
    lead_minutes: int
    reminded_by_change_id: ScheduleChangeId | None = None


def is_reminder_due(
    *, lead_minutes: int, positions_ahead: int, seconds_ahead: int | None
) -> bool:
    """``seconds_ahead`` is None when no planned duration backs an estimate;
    the running order alone decides then."""
    if positions_ahead <= 0:
        return False
    if positions_ahead <= REMINDER_POSITIONS_AHEAD:
        return True
    if seconds_ahead is None:
        return False
    return seconds_ahead <= lead_minutes * 60
