import asyncio
from typing import cast

from pydantic import BaseModel

from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.queries.schedule_changes import ScheduleChangeQuery
from fanfan.application.ports.queries.schedule_events import ScheduleEventQuery
from fanfan.application.ports.queries.subscriptions import SubscriptionQuery
from fanfan.application.ports.queries.users import UserQuery
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.template_renderer import TemplateRenderer
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.schedule import ScheduleChangeNotFound
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType


class SendScheduleChangeNotificationsInput(BaseModel):
    schedule_change_id: ScheduleChangeId


class SendScheduleChangeNotifications:
    def __init__(
        self,
        template_renderer: TemplateRenderer,
        changes_query: ScheduleChangeQuery,
        schedule_query: ScheduleEventQuery,
        user_query: UserQuery,
        subscription_query: SubscriptionQuery,
        mailing_repo: MailingRepository,
        trx: TransactionManager,
        events_broker: EventBroker,
    ):
        self.template_renderer = template_renderer
        self.changes_query = changes_query
        self.schedule_query = schedule_query
        self.user_query = user_query
        self.subscription_query = subscription_query
        self.mailing_repo = mailing_repo
        self.trx = trx
        self.events_broker = events_broker

    @staticmethod
    def _resolve_reason_msg(
        schedule_change: ScheduleChangeFullDTO,
    ) -> str | None:
        changed_event = schedule_change.changed_event
        argument_event = schedule_change.argument_event
        match schedule_change.type:
            case ScheduleChangeType.SET_AS_CURRENT:
                if changed_event:
                    return f"Выступление №{changed_event.public_number:03d} началось"
                if argument_event:
                    return (
                        f"Выступление №{argument_event.public_number:03d} "
                        f"больше не текущее"
                    )
            case ScheduleChangeType.MOVED:
                if changed_event:
                    return f"Выступление №{changed_event.public_number:03d} перенесено"
            case ScheduleChangeType.SKIPPED:
                if changed_event:
                    return f"Выступление №{changed_event.public_number:03d} было снято"
            case ScheduleChangeType.UNSKIPPED:
                if changed_event:
                    return f"Выступление №{changed_event.public_number:03d} вернулось"
        return None

    async def _build_editor_notifications(
        self, schedule_change: ScheduleChangeFullDTO, reason_msg: str | None
    ) -> list[NewNotificationEvent]:
        events: list[NewNotificationEvent] = []
        if schedule_change.user:
            editor = schedule_change.user
            editors = await self.user_query.read_schedule_editors()
            events.extend(
                NewNotificationEvent(
                    notification=NewNotificationDTO(
                        id=generate_notification_id(),
                        user_id=e.id,
                        title="Изменение расписания",
                        body=f"@{editor.username} сделал изменение "
                        f"в расписании: {reason_msg}",
                        type=NotificationType.SCHEDULE_CHANGE,
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
    ) -> list[NewNotificationEvent]:
        events: list[NewNotificationEvent] = []
        body = await self.template_renderer.render(
            "global_announcement.jinja2",
            {
                "current_event_public_number": current_event.public_number,
                "current_event_block_title": current_event.block_title,
                "current_event_nomination_title": current_event.nomination_title,
                "current_event_title": current_event.title,
                "next_event_public_number": next_event.public_number
                if next_event
                else None,
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
            NewNotificationEvent(
                notification=NewNotificationDTO(
                    id=generate_notification_id(),
                    user_id=u.id,
                    title="На сцене",
                    body=body,
                    type=NotificationType.SCHEDULE_CHANGE,
                    mailing_id=schedule_change.mailing_id,
                ),
            )
            for u in await self.user_query.read_all_by_receive_all_announcements()
        )
        return events

    async def _build_subscription_notifications(
        self,
        schedule_change: ScheduleChangeFullDTO,
        current_event: ScheduleEventFullDTO,
        changed_event: ScheduleChangeEventDTO,
        reason_msg: str | None,
    ) -> list[NewNotificationEvent]:
        events: list[NewNotificationEvent] = []
        # Queue always exists for current event
        current_event_queue = cast("int", current_event.queue)

        upcoming_subscriptions = (
            await self.subscription_query.read_upcoming_subscriptions(
                current_event_queue=current_event_queue
            )
        )
        for s in upcoming_subscriptions:
            if s.event.queue is None or s.event.time_until is None:
                continue
            if current_event.order <= changed_event.order <= s.event.order:
                body = await self.template_renderer.render(
                    "subscription_notification.jinja2",
                    {
                        "event_public_number": s.event.public_number,
                        "event_title": s.event.title,
                        "queue_difference": s.event.queue - current_event_queue,
                        "time_diff": s.event.time_until - current_event_queue,
                        "reason_msg": reason_msg,
                    },
                )
                events.append(
                    NewNotificationEvent(
                        notification=NewNotificationDTO(
                            id=generate_notification_id(),
                            user_id=s.user_id,
                            title="Уведомление о подписке",
                            body=body,
                            type=NotificationType.SCHEDULE_SUBSCRIPTION,
                            mailing_id=schedule_change.mailing_id,
                        )
                    )
                )
        return events

    async def __call__(self, data: SendScheduleChangeNotificationsInput) -> None:
        schedule_change = await self.changes_query.read_schedule_change(
            data.schedule_change_id
        )
        if schedule_change is None:
            raise ScheduleChangeNotFound
        current_event = await self.schedule_query.read_current_event()
        next_event = await self.schedule_query.read_next_event()
        changed_event = schedule_change.changed_event
        reason_msg = self._resolve_reason_msg(schedule_change)

        notification_events: list[NewNotificationEvent] = []
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
            notification_events.extend(
                await self._build_subscription_notifications(
                    schedule_change=schedule_change,
                    current_event=current_event,
                    changed_event=changed_event,
                    reason_msg=reason_msg,
                )
            )

        if schedule_change.mailing_id:
            await self.mailing_repo.set_total(
                mailing_id=schedule_change.mailing_id,
                total_count=len(notification_events),
            )
            await self.trx.commit()

        await asyncio.gather(
            *(self.events_broker.publish(e) for e in notification_events)
        )
