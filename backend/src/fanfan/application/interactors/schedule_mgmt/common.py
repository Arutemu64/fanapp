import math

from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.core.exceptions.schedule import ScheduleEditTooFast


async def ensure_announcement_cooldown(
    changes_gateway: ScheduleChangeGateway, cooldown_seconds: int
) -> None:
    """Reject an announced edit that comes too soon after the previous one.

    Call it after ``ScheduleEventGateway.lock_for_edit``: under that lock no
    other edit can record a change between this check and the commit, so the
    cooldown commits together with the edit and a failed edit never spends it.
    Every announced edit records a ScheduleChange, which is what makes the
    newest one the last announcement. Undo deletes its change, so an undone
    edit stops counting — its announcement was withdrawn with it.
    """
    elapsed = await changes_gateway.read_seconds_since_last_change()
    if elapsed is None or elapsed >= cooldown_seconds:
        return
    # Round up: Retry-After must not invite a retry that is still too early.
    raise ScheduleEditTooFast(retry_after=math.ceil(cooldown_seconds - elapsed))
