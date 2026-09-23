from dishka import AsyncContainer, FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.core.events.sync import SyncRequested
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
)

sync_router = NatsRouter()

# Resolved lazily by source rather than declared as FromDishka parameters:
# Dishka resolves constructor dependencies eagerly, and each vendor's config
# provider raises when that vendor is unset, so asking for both here would break
# a deployment that configures only one.
EXECUTORS = {
    SyncSource.COSPLAY2: ExecuteCosplaySync,
    SyncSource.TCLOUD: ExecuteTicketsSync,
}


@sync_router.subscriber(
    SyncRequested.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="run_requested_sync",
    # Redeliver on failure: FastStream's default for NATS, REJECT_ON_ERROR,
    # terminates the message, so one transient error would lose the event the
    # outbox delivered. Redelivery is bounded and delayed (redelivery.py).
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def run_requested_sync(
    data: SyncRequested,
    container: FromDishka[AsyncContainer],
    msg: NatsMessage,
) -> None:
    interactor = await container.get(EXECUTORS[data.source])
    # A sync can outlast AckWait; the heartbeat keeps a live run from being
    # redelivered needlessly. Correctness does not rest on it: the run lease in
    # SyncRunTracker.start() is what stops a second worker running it.
    async with in_progress_heartbeat(msg):
        await interactor(run_id=data.sync_run_id)
