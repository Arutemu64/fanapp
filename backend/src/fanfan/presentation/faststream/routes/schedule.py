from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.events.notifications import MailingCancelled
from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.presentation.faststream.jstream import stream

schedule_router = NatsRouter()


@schedule_router.subscriber(
    ScheduleChangeCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="process_schedule_change",
)
@inject
async def process_schedule_change(
    data: ScheduleChangeCreated,
    interactor: FromDishka[SendScheduleChangeNotifications],
    realtime_gateway: FromDishka[RealtimeGateway],
) -> None:
    await interactor(
        SendScheduleChangeNotificationsInput(schedule_change_id=data.schedule_change_id)
    )
    await realtime_gateway.publish(SSEMessage(SSEEventName.SCHEDULE_UPDATED))


@schedule_router.subscriber(
    ScheduleChangeUndone.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="undo_schedule_change",
)
@inject
async def undo_schedule_change(
    data: ScheduleChangeUndone,
    events_broker: FromDishka[EventBroker],
    realtime_gateway: FromDishka[RealtimeGateway],
) -> None:
    if data.mailing_id:
        await events_broker.publish(MailingCancelled(mailing_id=data.mailing_id))
    await realtime_gateway.publish(SSEMessage(SSEEventName.SCHEDULE_UPDATED))
