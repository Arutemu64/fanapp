import asyncio
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.template_renderer import TemplateRenderer
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.schedule_timing import apply_expected_start_times
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.schedule import ScheduleChangeNotFound
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId


class SendScheduleChangeNotificationsInput(BaseModel):
    schedule_change_id: ScheduleChangeId


class SendScheduleChangeNotifications:
    def __init__(
        self,
        template_renderer: TemplateRenderer,
        changes_gateway: ScheduleChangeGateway,
        schedule_gateway: ScheduleEventGateway,
        user_gateway: UserGateway,
        subscription_gateway: SubscriptionGateway,
        mailing_gateway: MailingGateway,
        settings_gateway: AppSettingsGateway,
        uow: UnitOfWork,
        events_broker: EventBroker,
    ):
        self.template_renderer = template_renderer
        self.changes_gateway = changes_gateway
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.subscription_gateway = subscription_gateway
        self.mailing_gateway = mailing_gateway
        self.settings_gateway = settings_gateway
        self.uow = uow
        self.events_broker = events_broker

    @staticmethod
    def _event_label(event: ScheduleChangeEventDTO) -> str:
        """Name an event inside a notification body.

        A numberless event (a break) is named by its title instead — it is the
        only handle the reader has, and there is no number to print.
        """
        if event.number is None:
            return f"«{event.title}»"
        return f"№{event.number:03d}"

    @classmethod
    def _resolve_reason_msg(
        cls,
        schedule_change: ScheduleChangeFullDTO,
    ) -> str | None:
        changed_event = schedule_change.changed_event
        argument_event = schedule_change.argument_event
        match schedule_change.type:
            case ScheduleChangeType.SET_AS_CURRENT:
                if changed_event:
                    return f"Выступление {cls._event_label(changed_event)} началось"
                if argument_event:
                    return (
                        f"Выступление {cls._event_label(argument_event)} "
                        f"больше не текущее"
                    )
            case ScheduleChangeType.MOVED:
                if changed_event:
                    return f"Выступление {cls._event_label(changed_event)} перенесено"
            case ScheduleChangeType.SKIPPED:
                if changed_event:
                    return f"Выступление {cls._event_label(changed_event)} было снято"
            case ScheduleChangeType.UNSKIPPED:
                if changed_event:
                    return f"Выступление {cls._event_label(changed_event)} вернулось"
        return None

    async def _build_editor_notifications(
        self, schedule_change: ScheduleChangeFullDTO, reason_msg: str | None
    ) -> list[NotificationQueued]:
        events: list[NotificationQueued] = []
        if schedule_change.user:
            editor = schedule_change.user
            editors = await self.user_gateway.read_schedule_editors()
            events.extend(
                NotificationQueued(
                    notification=NewNotification(
                        id=generate_notification_id(),
                        user_id=e.id,
                        title="Изменение расписания",
                        body=f"@{editor.username} сделал изменение "
                        f"в расписании: {reason_msg}",
                        type=NotificationType.SCHEDULE_CHANGE,
                        path="/schedule/changes",
                        mailing_id=schedule_change.mailing_id,
                    )
                )
                for e in editors
            )
        return events

    async def _build_global_announcement_notifications(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        next_event: ScheduleEventFullDTO | None,
    ) -> list[NotificationQueued]:
        events: list[NotificationQueued] = []
        body = await self.template_renderer.render(
            "global_announcement.jinja2",
            {
                "current_event_number": current_event.number,
                "current_event_block_title": current_event.block_title,
                "current_event_nomination_title": current_event.nomination_title,
                "current_event_title": current_event.title,
                "next_event_number": next_event.number if next_event else None,
                "next_event_block_title": next_event.block_title
                if next_event
                else None,
                "next_event_nomination_title": next_event.nomination_title
                if next_event
                else None,
                "next_event_title": next_event.title if next_event else None,
            },
        )
        events.extend(
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=u.id,
                    title="На сцене",
                    body=body,
                    type=NotificationType.SCHEDULE_CHANGE,
                    path="/schedule",
                    mailing_id=schedule_change.mailing_id,
                ),
            )
            for u in await self.user_gateway.read_all_by_receive_all_announcements()
        )
        return events

    async def _build_subscription_notifications(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        changed_event: ScheduleChangeEventDTO,
        reason_msg: str | None,
        expected_start_times: dict[ScheduleEventId, datetime | None],
    ) -> list[NotificationQueued]:
        events: list[NotificationQueued] = []
        # Queue always exists for the (non-skipped) current event.
        current_event_queue = cast("int", current_event.queue)

        upcoming_subscriptions = (
            await self.subscription_gateway.read_upcoming_subscriptions(
                current_event_queue=current_event_queue
            )
        )
        for s in upcoming_subscriptions:
            if s.event.queue is None:
                continue
            if current_event.order <= changed_event.order <= s.event.order:
                body = await self.template_renderer.render(
                    "subscription_notification.jinja2",
                    {
                        "event_number": s.event.number,
                        "event_title": s.event.title,
                        "queue_difference": s.event.queue - current_event_queue,
                        # Absolute drift-aware start (ADR-0008); None when there is
                        # no live anchor yet, and the template omits the time then.
                        "expected_start_time": expected_start_times.get(s.event.id),
                        "reason_msg": reason_msg,
                    },
                )
                events.append(
                    NotificationQueued(
                        notification=NewNotification(
                            id=generate_notification_id(),
                            user_id=s.user_id,
                            title="Уведомление о подписке",
                            body=body,
                            type=NotificationType.SCHEDULE_SUBSCRIPTION,
                            path="/schedule",
                            mailing_id=schedule_change.mailing_id,
                        )
                    )
                )
        return events

    async def __call__(self, data: SendScheduleChangeNotificationsInput) -> None:
        schedule_change = await self.changes_gateway.read_schedule_change(
            data.schedule_change_id
        )
        if schedule_change is None:
            raise ScheduleChangeNotFound
        current_event = await self.schedule_gateway.read_current_event()
        next_event = await self.schedule_gateway.read_next_event()
        changed_event = schedule_change.changed_event
        reason_msg = self._resolve_reason_msg(schedule_change)

        notification_events: list[NotificationQueued] = []
        notification_events.extend(
            await self._build_editor_notifications(schedule_change, reason_msg)
        )
        if schedule_change.next_event_changed and current_event:
            notification_events.extend(
                await self._build_global_announcement_notifications(
                    schedule_change=schedule_change,
                    current_event=current_event,
                    next_event=next_event,
                )
            )
        if current_event and changed_event:
            # Project absolute start times once, reusing the same schedule-read
            # timing service the schedule uses. The push renders the absolute
            # "примерно в HH:MM" — not the screen's live countdown: a delivered
            # notification is read at an unknown later time and can't tick, so an
            # absolute time stays correct where a relative one would be stale.
            settings = await self.settings_gateway.get()
            projected = apply_expected_start_times(
                await self.schedule_gateway.read_list_schedule(),
                transition_buffer=settings.limits.transition_buffer,
                now=datetime.now(UTC),
            )
            expected_start_times: dict[ScheduleEventId, datetime | None] = {
                e.id: e.expected_start_time for e in projected
            }
            notification_events.extend(
                await self._build_subscription_notifications(
                    schedule_change=schedule_change,
                    current_event=current_event,
                    changed_event=changed_event,
                    reason_msg=reason_msg,
                    expected_start_times=expected_start_times,
                )
            )

        if schedule_change.mailing_id:
            await self.mailing_gateway.set_total(
                mailing_id=schedule_change.mailing_id,
                total_count=len(notification_events),
            )
            await self.uow.commit()

        await asyncio.gather(
            *(self.events_broker.publish(e) for e in notification_events)
        )
