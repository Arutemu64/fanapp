from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.notifications import MailingCancelled
from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.presentation.faststream.headers import read_occurred_at
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
)

schedule_router = NatsRouter()


@schedule_router.subscriber(
    ScheduleChangeCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="process_schedule_change",
    # Redeliver on failure: FastStream's default for NATS, REJECT_ON_ERROR,
    # terminates the message, so one transient error would lose the event the
    # outbox delivered. Redelivery is bounded and delayed (redelivery.py).
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
    # A large fan-out can outlast AckWait while NATS is slow to ack; the
    # heartbeat keeps a live run from being redelivered on top of itself. It
    # covers the live update too, whose cache warm-up waits on the edit lock.
    async with in_progress_heartbeat(msg):
        # Live update before the notification fan-out: the screen should not wait
        # on building a notification per subscriber, nor on a fan-out failure
        # that redelivers this message. A redelivery repeats the live update,
        # which is harmless — clients revalidate and get a 304 for a schedule
        # they already hold.
        await publish_schedule_updated()
        await interactor(
            SendScheduleChangeNotificationsInput(
                schedule_change_id=data.schedule_change_id,
                occurred_at=read_occurred_at(msg),
            )
        )


@schedule_router.subscriber(
    ScheduleChangeUndone.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="undo_schedule_change",
    # Redeliver on failure: FastStream's default for NATS, REJECT_ON_ERROR,
    # terminates the message, so one transient error would lose the event the
    # outbox delivered. Redelivery is bounded and delayed (redelivery.py).
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def undo_schedule_change(
    data: ScheduleChangeUndone,
    events_broker: FromDishka[EventBroker],
    publish_schedule_updated: FromDishka[PublishScheduleUpdated],
) -> None:
    # Cancel first: until it lands, notifications queued for the undone change
    # can still go out, so it must not wait on the cache warm-up or fail with
    # the live update.
    if data.mailing_id:
        await events_broker.publish(MailingCancelled(mailing_id=data.mailing_id))
    await publish_schedule_updated()
