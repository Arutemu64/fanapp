from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.schedule_mgmt.process_schedule_change import (
    ProcessScheduleChange,
    ProcessScheduleChangeCommand,
)
from fanfan.application.sse.stream_events import SSEMessage
from fanfan.core.events.notifications import CancelMailingEvent
from fanfan.core.events.schedule import (
    CreatedScheduleChangeEvent,
    UndoScheduleChangeEvent,
)
from fanfan.presentation.faststream.jstream import stream

schedule_router = NatsRouter()


@schedule_router.subscriber(
    CreatedScheduleChangeEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="process_schedule_change",
)
@inject
async def process_schedule_change(
    data: CreatedScheduleChangeEvent,
    interactor: FromDishka[ProcessScheduleChange],
    events_broker: FromDishka[EventBroker],
) -> None:
    await interactor(
        ProcessScheduleChangeCommand(schedule_change_id=data.schedule_change_id)
    )
    await events_broker.push_sse_message(SSEMessage("update_schedule"))


@schedule_router.subscriber(
    UndoScheduleChangeEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="undo_schedule_change",
)
@inject
async def undo_schedule_change(
    data: UndoScheduleChangeEvent,
    events_broker: FromDishka[EventBroker],
) -> None:
    if data.mailing_id:
        await events_broker.publish(CancelMailingEvent(mailing_id=data.mailing_id))
    await events_broker.push_sse_message(SSEMessage("update_schedule"))
