import asyncio
from dataclasses import dataclass

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.subscriptions import SubscriptionGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.jinja.factory import StreamJinjaEnvironment
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.core.dto.notification import NewNotificationDTO
from fanfan.core.dto.schedule import ScheduleEventFullDTO
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType


@dataclass(slots=True, frozen=True)
class ProcessScheduleChangeCommand:
    schedule_change_id: ScheduleChangeId


def _get_schedule_change_reason_msg(
    schedule_change: ScheduleChange,
    changed_event: ScheduleEventFullDTO | None,
    argument_event: ScheduleEventFullDTO | None,
) -> str | None:
    match schedule_change.type:
        case ScheduleChangeType.SET_AS_CURRENT:
            if changed_event:
                return f"🔥 Выступление №{changed_event.public_number:03d} началось"
            if argument_event:
                return f"⛔ Выступление №{argument_event.public_number:03d} больше не текущее"
        case ScheduleChangeType.MOVED:
            return f"🔀 Выступление №{changed_event.public_number:03d} перенесено"
        case ScheduleChangeType.SKIPPED:
            return f"🚫 Выступление №{changed_event.public_number:03d} было снято"
        case ScheduleChangeType.UNSKIPPED:
            return f"🙉 Выступление №{changed_event.public_number:03d} вернулось"
    return None


class ProcessScheduleChange:
    def __init__(
        self,
        config: EnvConfig,
        jinja: StreamJinjaEnvironment,
        changes_gateway: ScheduleChangeGateway,
        schedule_gateway: ScheduleEventGateway,
        user_gateway: UserGateway,
        subscription_gateway: SubscriptionGateway,
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
        events_broker: EventBroker,
    ):
        self.config = config
        self.jinja = jinja
        self.changes_gateway = changes_gateway
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.subscription_gateway = subscription_gateway
        self.mailing_gateway = mailing_gateway
        self.uow = uow
        self.events_broker = events_broker

    async def __call__(self, data: ProcessScheduleChangeCommand) -> None:
        # Prepare templates
        global_announcement_template = self.jinja.get_template(
            "global_announcement.jinja2",
        )
        subscription_template = self.jinja.get_template(
            "subscription_notification.jinja2",
        )

        # Get schedule change and events
        schedule_change = await self.changes_gateway.get_schedule_change(
            data.schedule_change_id
        )
        changed_event = (
            await self.schedule_gateway.read_event_by_id(
                schedule_change.changed_event_id
            )
            if schedule_change.changed_event_id
            else None
        )
        argument_event = (
            await self.schedule_gateway.read_event_by_id(
                schedule_change.argument_event_id
            )
            if schedule_change.argument_event_id
            else None
        )

        # Generate reason message
        reason_msg = _get_schedule_change_reason_msg(
            schedule_change=schedule_change,
            changed_event=changed_event,
            argument_event=argument_event,
        )

        notification_events: list[NewNotificationEvent] = []

        # Notify editors
        editor = await self.user_gateway.get_user_by_id(schedule_change.user_id)
        notification_events.extend(
            NewNotificationEvent(
                notification=NewNotificationDTO(
                    user_id=e.id,
                    title="Изменение расписания",
                    body=f"@{editor.username} сделал изменение в расписании:\n{reason_msg}",
                    type=NotificationType.SCHEDULE_CHANGE,
                    mailing_id=schedule_change.mailing_id,
                )
            )
            for e in await self.user_gateway.read_schedule_editors()
        )

        current_event = await self.schedule_gateway.read_current_event()
        next_event = (
            await self.schedule_gateway.read_next_event() if current_event else None
        )

        # Global announcement
        if schedule_change.send_global_announcement and current_event:
            body = await global_announcement_template.render_async(
                {
                    "current_event": current_event,
                    "next_event": next_event,
                }
            )
            notification_events.extend(
                NewNotificationEvent(
                    notification=NewNotificationDTO(
                        user_id=u.id,
                        title="На сцене",
                        body=body,
                        type=NotificationType.SCHEDULE_CHANGE,
                        mailing_id=schedule_change.mailing_id,
                    ),
                )
                for u in await self.user_gateway.read_all_by_receive_all_announcements()
            )

            # Subscriptions
            if current_event and changed_event:
                upcoming_subscriptions = (
                    await self.subscription_gateway.read_upcoming_subscriptions(
                        current_event_queue=current_event.queue
                    )
                )
                for s in upcoming_subscriptions:
                    if current_event.order <= changed_event.order <= s.event.order:
                        # Read full event to load queue and time_until
                        body = await subscription_template.render_async(
                            {
                                "event_public_number": s.event.public_number,
                                "event_title": s.event.title,
                                "queue_difference": s.event.queue - current_event.queue,
                                "time_diff": s.event.time_until
                                - current_event.time_until,
                                "reason_msg": reason_msg,
                            }
                        )
                        notification_events.append(
                            NewNotificationEvent(
                                notification=NewNotificationDTO(
                                    user_id=s.user_id,
                                    title="Уведомление о подписке",
                                    body=body,
                                    type=NotificationType.SCHEDULE_SUBSCRIPTION,
                                    mailing_id=schedule_change.mailing_id,
                                )
                            )
                        )

            async with self.uow:
                mailing = await self.mailing_gateway.get_mailing(
                    schedule_change.mailing_id,
                    lock=True,
                )
                if mailing:
                    mailing.update_total(len(notification_events))
                    await self.mailing_gateway.save_mailing(mailing)
                    await self.uow.commit()

            await asyncio.gather(
                *(self.events_broker.publish(e) for e in notification_events)
            )
