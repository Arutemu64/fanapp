import logging
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
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
from fanfan.core.vo.notification import (
    SCHEDULE_NOTIFICATION_LIFETIME,
    NotificationType,
    schedule_notification_id_for,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType

logger = logging.getLogger(__name__)


# The notifications describe the schedule as it is when they are built (current
# and next event are read now, not at change time), so a change processed long
# after it was made announces the wrong event. Past the lifetime it is dropped:
# delivery is only this late after an outage (relay retries, NATS or consumer
# down), and a stale "event started" push is worse than none.
def _is_stale(occurred_at: datetime | None) -> bool:
    if occurred_at is None:
        return False
    return datetime.now(UTC) - occurred_at > SCHEDULE_NOTIFICATION_LIFETIME


class SendScheduleChangeNotificationsInput(BaseModel):
    schedule_change_id: ScheduleChangeId
    # When the change was committed. None when unknown (a message relayed before
    # the timestamp was sent), which is treated as fresh.
    occurred_at: datetime | None = None


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

    async def _build_subscription_notifications(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        changed_event: ScheduleChangeEntryDTO,
        reason_msg: str | None,
    ) -> list[NewNotification]:
        notifications: list[NewNotification] = []
        # Queue always exists for the (non-skipped) current event.
        current_event_position = cast("int", current_event.position)

        upcoming_subscriptions = (
            await self.subscription_gateway.read_upcoming_subscriptions(
                current_event_position=current_event_position
            )
        )
        for s in upcoming_subscriptions:
            if s.event.position is None:
                continue
            if current_event.order <= changed_event.order <= s.event.order:
                body = await self.template_renderer.render(
                    "subscription_notification.jinja2",
                    {
                        "event_number": s.event.number,
                        "event_title": s.event.title,
                        "position_difference": s.event.position
                        - current_event_position,
                        "reason_msg": reason_msg,
                    },
                )
                notifications.append(
                    NewNotification(
                        id=schedule_notification_id_for(
                            schedule_change.id, s.user_id, f"subscription:{s.id}"
                        ),
                        user_id=s.user_id,
                        title="Уведомление о подписке",
                        body=body,
                        type=NotificationType.SCHEDULE_SUBSCRIPTION,
                        path="/schedule",
                        mailing_id=schedule_change.mailing_id,
                    )
                )
        return notifications

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

    async def abandon(self, data: SendScheduleChangeNotificationsInput) -> None:
        """Fail the change's mailing when its fan-out will not be retried again."""
        # The failed run can leave the transaction aborted.
        await self.uow.rollback()
        schedule_change = await self.changes_gateway.read_schedule_change(
            data.schedule_change_id
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
            notifications.extend(
                await self._build_subscription_notifications(
                    schedule_change=schedule_change,
                    current_event=current_event,
                    changed_event=changed_event,
                    reason_msg=reason_msg,
                )
            )
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
