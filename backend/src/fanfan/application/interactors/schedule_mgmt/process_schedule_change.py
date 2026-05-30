import asyncio
from typing import cast

from pydantic import BaseModel

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.jinja.factory import JinjaEnvironment
from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.queries.schedule_changes import ScheduleChangeQuery
from fanfan.application.ports.queries.schedule_events import ScheduleEventQuery
from fanfan.application.ports.queries.subscriptions import SubscriptionQuery
from fanfan.application.ports.queries.users import UserQuery
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.schedule import ScheduleChangeNotFound
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType


class ProcessScheduleChangeInput(BaseModel):
    schedule_change_id: ScheduleChangeId


def _get_schedule_change_reason_msg(
    schedule_change: ScheduleChangeFullDTO,
) -> str | None:
    changed_event = schedule_change.changed_event
    argument_event = schedule_change.argument_event
    match schedule_change.type:
        case ScheduleChangeType.SET_AS_CURRENT:
            if changed_event:
                return f"🔥 Выступление №{changed_event.public_number:03d} началось"
            if argument_event:
                return (
                    f"⛔ Выступление №{argument_event.public_number:03d} "
                    f"больше не текущее"
                )
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
        jinja: JinjaEnvironment,
        changes_query: ScheduleChangeQuery,
        schedule_query: ScheduleEventQuery,
        user_repo: UserRepository,
        user_query: UserQuery,
        subscription_query: SubscriptionQuery,
        mailing_repo: MailingRepository,
        trx: TransactionManager,
        events_broker: EventBroker,
    ):
        self.config = config
        self.jinja = jinja
        self.changes_query = changes_query
        self.schedule_query = schedule_query
        self.user_repo = user_repo
        self.user_query = user_query
        self.subscription_query = subscription_query
        self.mailing_repo = mailing_repo
        self.trx = trx
        self.events_broker = events_broker

    async def __call__(self, data: ProcessScheduleChangeInput) -> None:
        # Prepare templates
        global_announcement_template = self.jinja.get_template(
            "global_announcement.jinja2",
        )
        subscription_template = self.jinja.get_template(
            "subscription_notification.jinja2",
        )

        # Get schedule change and events
        schedule_change = await self.changes_query.read_schedule_change(
            data.schedule_change_id
        )
        if schedule_change is None:
            raise ScheduleChangeNotFound
        changed_event = schedule_change.changed_event

        # Generate reason message
        reason_msg = _get_schedule_change_reason_msg(schedule_change)

        notification_events: list[NewNotificationEvent] = []

        # Notify editors
        if schedule_change.user_id and (
            editor := await self.user_repo.get_by_id(schedule_change.user_id)
        ):
            notification_events.extend(
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
                for e in await self.user_query.read_schedule_editors()
            )

        current_event = await self.schedule_query.read_current_event()
        next_event = (
            await self.schedule_query.read_next_event() if current_event else None
        )

        # Global announcement
        if schedule_change.send_global_announcement and current_event:
            # TODO pass specific values
            body = await global_announcement_template.render_async(
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
                }
            )
            notification_events.extend(
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

            # Subscriptions
            if current_event and changed_event:
                current_event_queue = cast("int", current_event.queue)
                upcoming_subscriptions = (
                    await self.subscription_query.read_upcoming_subscriptions(
                        current_event_queue=current_event_queue
                    )
                )
                for s in upcoming_subscriptions:
                    if current_event.order <= changed_event.order <= s.event.order:
                        # Read full event to load queue and time_until
                        body = await subscription_template.render_async(
                            {
                                "event_public_number": s.event.public_number,
                                "event_title": s.event.title,
                                "queue_difference": s.event.queue - current_event_queue,
                                "time_diff": s.event.time_until - current_event_queue,
                                "reason_msg": reason_msg,
                            }
                        )
                        notification_events.append(
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

            if schedule_change.mailing_id:
                mailing = await self.mailing_repo.get(schedule_change.mailing_id)
                if mailing:
                    mailing.update_total(len(notification_events))
                    await self.mailing_repo.save(mailing)
                    await self.trx.commit()

            await asyncio.gather(
                *(self.events_broker.publish(e) for e in notification_events)
            )
