from dishka import AsyncContainer, FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.commands.sync import RunSyncCommand
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
)

sync_router = NatsRouter()

EXECUTORS = {
    SyncSource.COSPLAY2: ExecuteCosplaySync,
    SyncSource.TCLOUD: ExecuteTicketsSync,
}


@sync_router.subscriber(
    RunSyncCommand.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="run_requested_sync",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def run_requested_sync(
    data: RunSyncCommand,
    container: FromDishka[AsyncContainer],
    msg: NatsMessage,
) -> None:
    interactor = await container.get(EXECUTORS[data.source])
    async with in_progress_heartbeat(msg):
        await interactor(run_id=data.sync_run_id)
