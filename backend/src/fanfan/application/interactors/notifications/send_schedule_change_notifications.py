import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEntryDTO, ScheduleEventFullDTO
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEntryDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.template_renderer import TemplateRenderer
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.notification_fan_out import NotificationFanOut
from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.exceptions.schedule import ScheduleChangeNotFound
from fanfan.core.models.notification import NewNotification
from fanfan.core.models.subscription import is_reminder_due
from fanfan.core.vo.notification import (
    SCHEDULE_NOTIFICATION_LIFETIME,
    NotificationType,
    schedule_notification_id_for,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.subscription import SubscriptionId

logger = logging.getLogger(__name__)


# The notifications describe the schedule as it is when they are built (current
# and next event are read now, not at change time), so a change processed long
# after it was made announces the wrong event. Past the lifetime it is dropped:
# delivery is only this late after an outage (relay retries, NATS or consumer
# down), and a stale "event started" push is worse than none.
def _is_stale(occurred_at: datetime) -> bool:
    return datetime.now(UTC) - occurred_at > SCHEDULE_NOTIFICATION_LIFETIME


def _seconds_ahead_by_position(
    schedule: Sequence[ScheduleEntryDTO], current_event_position: int
) -> dict[int, int]:
    """Planned stage time before each act from the current one on, by position.

    The current act counts in full, as when it started is not known here; with
    the durations being upper limits too, the estimate runs early, which is the
    side a reminder can afford to err on. The schedule screen shows the same
    sum (frontend secondsUntilActs; ADR-0043).
    """
    seconds_ahead: dict[int, int] = {}
    elapsed = 0
    for entry in schedule:
        if not isinstance(entry, ScheduleEventFullDTO) or entry.position is None:
            continue
        if entry.position < current_event_position:
            continue
        seconds_ahead[entry.position] = elapsed
        elapsed += entry.duration
    return seconds_ahead


@dataclass(slots=True)
class _SubscriptionNotices:
    notifications: list[NewNotification] = field(default_factory=list)
    # Subscriptions this change reminds, and those it re-arms.
    reminded: list[SubscriptionId] = field(default_factory=list)
    rearmed: list[SubscriptionId] = field(default_factory=list)


_SUBSCRIPTION_TITLES = {
    "soon": "Скоро на сцене",
    "started": "Уже на сцене",
    "changed": "Выступление из подписок изменилось",
}


class SendScheduleChangeNotificationsInput(BaseModel):
    schedule_change_id: ScheduleChangeId
    # When the change was committed.
    occurred_at: datetime


class SendScheduleChangeNotifications:
    def __init__(
        self,
        template_renderer: TemplateRenderer,
        changes_gateway: ScheduleChangeGateway,
        schedule_gateway: ScheduleEntryGateway,
        user_gateway: UserGateway,
        subscription_gateway: SubscriptionGateway,
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
        fan_out: NotificationFanOut,
    ) -> None:
        self.template_renderer = template_renderer
        self.changes_gateway = changes_gateway
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.subscription_gateway = subscription_gateway
        self.mailing_gateway = mailing_gateway
        self.uow = uow
        self.fan_out = fan_out

    async def _render_reason_msg(
        self, schedule_change: ScheduleChangeFullDTO
    ) -> str | None:
        changed_event = schedule_change.changed_event
        event = changed_event
        # Unchecking the current event leaves no new current event; the reason
        # then names the event that left the stage.
        if event is None and schedule_change.type is ScheduleChangeType.SET_AS_CURRENT:
            event = schedule_change.related_entry
        if event is None:
            return None
        reason_msg = await self.template_renderer.render(
            "schedule_change_reason.txt.jinja2",
            {
                "change_type": schedule_change.type,
                "left_stage": changed_event is None,
                "event_number": event.number,
                "event_title": event.title,
            },
        )
        return reason_msg.strip() or None

    async def _build_editor_notifications(
        self, schedule_change: ScheduleChangeFullDTO, reason_msg: str | None
    ) -> list[NewNotification]:
        notifications: list[NewNotification] = []
        if schedule_change.user:
            editor = schedule_change.user
            editors = await self.user_gateway.read_schedule_editors()
            body = await self.template_renderer.render(
                "schedule_change_editor.jinja2",
                {"editor_username": editor.username, "reason_msg": reason_msg},
            )
            notifications.extend(
                NewNotification(
                    id=schedule_notification_id_for(schedule_change.id, e.id, "editor"),
                    user_id=e.id,
                    title="Изменение программы",
                    body=body,
                    type=NotificationType.SCHEDULE_CHANGE,
                    path="/schedule/changes",
                    mailing_id=schedule_change.mailing_id,
                )
                for e in editors
            )
        return notifications

    async def _build_global_announcement_notifications(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        next_event: ScheduleEventFullDTO | None,
    ) -> list[NewNotification]:
        notifications: list[NewNotification] = []
        body = await self.template_renderer.render(
            "global_announcement.jinja2",
            {
                "current_event_number": current_event.number,
                "current_event_nomination_title": current_event.nomination_title,
                "current_event_title": current_event.title,
                "next_event_number": next_event.number if next_event else None,
                "next_event_nomination_title": next_event.nomination_title
                if next_event
                else None,
                "next_event_title": next_event.title if next_event else None,
            },
        )
        notifications.extend(
            NewNotification(
                id=schedule_notification_id_for(
                    schedule_change.id, user_id, "announcement"
                ),
                user_id=user_id,
                title="На сцене",
                body=body,
                type=NotificationType.SCHEDULE_CHANGE,
                path="/schedule",
                mailing_id=schedule_change.mailing_id,
            )
            for user_id in (
                await self.user_gateway.read_ids_receiving_all_announcements()
            )
        )
        return notifications

    async def _build_subscription_notices(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        changed_event: ScheduleChangeEntryDTO,
        reason_msg: str | None,
    ) -> _SubscriptionNotices:
        """One notice per moment a subscriber acts on, not one per step.

        The act going on stage, the act itself moving or leaving, and a single
        reminder once it is due; acts passing by in between say nothing.
        """
        notices = _SubscriptionNotices()
        # Queue always exists for the (non-skipped) current event.
        current_event_position = cast("int", current_event.position)
        seconds_ahead = _seconds_ahead_by_position(
            await self.schedule_gateway.read_list_schedule(), current_event_position
        )
        subscriptions = await self.subscription_gateway.read_subscriptions_to_notify(
            current_event_position=current_event_position,
            changed_event_id=changed_event.id,
        )
        for s in subscriptions:
            positions_ahead: int | None = None
            minutes_ahead: int | None = None
            reminder_due = False
            if s.event.position is not None:
                positions_ahead = s.event.position - current_event_position
                event_seconds_ahead = seconds_ahead.get(s.event.position, 0)
                minutes_ahead = math.ceil(event_seconds_ahead / 60)
                reminder_due = is_reminder_due(
                    lead_minutes=s.lead_minutes,
                    positions_ahead=positions_ahead,
                    seconds_ahead=event_seconds_ahead,
                )

            is_own_change = s.event.id == changed_event.id
            if (
                is_own_change
                and schedule_change.type is ScheduleChangeType.SET_AS_CURRENT
            ):
                kind = "started"
            elif is_own_change:
                kind = "changed"
                # The act moved, left or came back, so whatever reminder it had
                # was about its old place: this notice is the reminder when the
                # act is already close, otherwise one is due again later.
                if reminder_due:
                    notices.reminded.append(s.id)
                else:
                    notices.rearmed.append(s.id)
            elif reminder_due and s.reminded_by_change_id in {
                None,
                schedule_change.id,
            }:
                kind = "soon"
                notices.reminded.append(s.id)
            else:
                continue

            body = await self.template_renderer.render(
                "subscription_notification.jinja2",
                {
                    "kind": kind,
                    "event_number": s.event.number,
                    "event_title": s.event.title,
                    "positions_ahead": positions_ahead,
                    "minutes_ahead": minutes_ahead,
                    "reason_msg": reason_msg,
                },
            )
            notices.notifications.append(
                NewNotification(
                    id=schedule_notification_id_for(
                        schedule_change.id, s.user_id, f"subscription:{s.id}"
                    ),
                    user_id=s.user_id,
                    title=_SUBSCRIPTION_TITLES[kind],
                    body=body,
                    type=NotificationType.SCHEDULE_SUBSCRIPTION,
                    path="/schedule",
                    mailing_id=schedule_change.mailing_id,
                    event_id=s.event.id,
                )
            )
        return notices

    async def _fail_mailing(self, schedule_change: ScheduleChangeFullDTO) -> None:
        if schedule_change.mailing_id is None:
            return
        mailing = await self.mailing_gateway.get(schedule_change.mailing_id)
        if mailing is None:
            return
        # Settle the mailing so it does not stay PENDING forever. A first
        # attempt may have stored some notifications before failing; the
        # mailing still fails, since its fan-out never finished.
        mailing.mark_failed()
        await self.mailing_gateway.save(mailing)
        await self.uow.commit()

    async def abandon(self, schedule_change_id: ScheduleChangeId) -> None:
        """Fail the change's mailing when its fan-out will not be retried again."""
        # The failed run can leave the transaction aborted.
        await self.uow.rollback()
        schedule_change = await self.changes_gateway.read_schedule_change(
            schedule_change_id
        )
        if schedule_change is None:
            return
        await self._fail_mailing(schedule_change)

    async def __call__(self, data: SendScheduleChangeNotificationsInput) -> None:
        schedule_change = await self.changes_gateway.read_schedule_change(
            data.schedule_change_id
        )
        if schedule_change is None:
            raise ScheduleChangeNotFound
        if _is_stale(data.occurred_at):
            logger.warning(
                "Stale schedule change dropped without notifications",
                extra={"schedule_change_id": str(schedule_change.id)},
            )
            await self._fail_mailing(schedule_change)
            return
        current_event = await self.schedule_gateway.read_current_event()
        next_event = await self.schedule_gateway.read_next_event()
        changed_event = schedule_change.changed_event
        reason_msg = await self._render_reason_msg(schedule_change)

        # Built in delivery order: the fan-out stores and sends in chunks, so
        # whoever comes first is notified first. A subscriber's own act moving
        # is the most time-critical news; the stage announcement goes to every
        # opt-in and can be large; the handful of editors made the change and
        # watch it live.
        notifications: list[NewNotification] = []
        if current_event and changed_event:
            subscription_notices = await self._build_subscription_notices(
                schedule_change=schedule_change,
                current_event=current_event,
                changed_event=changed_event,
                reason_msg=reason_msg,
            )
            # Recorded before the fan-out, not after: a fan-out that fails
            # midway is redelivered, and the reminder is keyed by this change,
            # so the rerun rebuilds the same notices rather than losing them.
            await self.subscription_gateway.set_reminded_by(
                subscription_notices.reminded, schedule_change.id
            )
            await self.subscription_gateway.set_reminded_by(
                subscription_notices.rearmed, None
            )
            await self.uow.commit()
            notifications.extend(subscription_notices.notifications)
        if schedule_change.next_event_changed and current_event:
            notifications.extend(
                await self._build_global_announcement_notifications(
                    schedule_change=schedule_change,
                    current_event=current_event,
                    next_event=next_event,
                )
            )
        notifications.extend(
            await self._build_editor_notifications(schedule_change, reason_msg)
        )

        try:
            await self.fan_out(notifications, mailing_id=schedule_change.mailing_id)
        except MailingAlreadyCancelled:
            # Undone before or during the fan-out; the cancellation removes
            # what was stored.
            logger.info(
                "Schedule change undone before its fan-out finished",
                extra={"schedule_change_id": str(schedule_change.id)},
            )
