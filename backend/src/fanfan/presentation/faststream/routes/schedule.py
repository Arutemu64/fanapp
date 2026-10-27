from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.commands.notifications import CancelMailingCommand
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.presentation.faststream.headers import read_occurred_at
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
    is_last_delivery,
)

schedule_router = NatsRouter()


@schedule_router.subscriber(
    ScheduleChangeCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="process_schedule_change",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def process_schedule_change(
    data: ScheduleChangeCreated,
    interactor: FromDishka[SendScheduleChangeNotifications],
    publish_schedule_updated: FromDishka[PublishScheduleUpdated],
    msg: NatsMessage,
) -> None:
    async with in_progress_heartbeat(msg):
        try:
            await publish_schedule_updated()
            await interactor(
                SendScheduleChangeNotificationsInput(
                    schedule_change_id=data.schedule_change_id,
                    occurred_at=read_occurred_at(msg),
                )
            )
        except Exception:
            if is_last_delivery(msg.raw_message):
                await interactor.abandon(data.schedule_change_id)
            raise


@schedule_router.subscriber(
    ScheduleChangeUndone.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="undo_schedule_change",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def undo_schedule_change(
    data: ScheduleChangeUndone,
    events_broker: FromDishka[EventBroker],
    publish_schedule_updated: FromDishka[PublishScheduleUpdated],
) -> None:
    if data.mailing_id:
        await events_broker.publish(CancelMailingCommand(mailing_id=data.mailing_id))
    await publish_schedule_updated()
