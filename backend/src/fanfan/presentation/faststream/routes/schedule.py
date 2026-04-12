from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.interactors.schedule_mgmt.process_schedule_change import (
    ProcessScheduleChange,
    ProcessScheduleChangeInput,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.realtime_gateway import RealtimeGateway
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
    realtime_gateway: FromDishka[RealtimeGateway],
) -> None:
    await interactor(
        ProcessScheduleChangeInput(schedule_change_id=data.schedule_change_id)
    )
    await realtime_gateway.publish(SSEMessage("update_schedule"))


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
    realtime_gateway: FromDishka[RealtimeGateway],
) -> None:
    if data.mailing_id:
        await events_broker.publish(CancelMailingEvent(mailing_id=data.mailing_id))
    await realtime_gateway.publish(SSEMessage("update_schedule"))
