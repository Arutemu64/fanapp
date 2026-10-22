from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId

# However long the estimate says the wait is, a reminder is due once the act is
# this many positions from the stage. Durations are planned, not measured, and a
# missing one counts as zero, so near the stage the running order is the
# reliable signal and the clock is not.
REMINDER_POSITIONS_AHEAD = 2


@dataclass(slots=True, kw_only=True)
class Subscription(AggregateRoot):
    id: SubscriptionId
    user_id: UserId
    event_id: ScheduleEntryId
    # How long before the act starts to remind, as estimated from the planned
    # durations of the acts ahead of it.
    lead_minutes: int
    # The schedule change whose notice carried the reminder; None until one
    # has. Keyed by change, not a flag, so a redelivered change rebuilds the
    # same reminder, and undoing that change (which deletes it) re-arms it.
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
