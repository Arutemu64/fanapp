from dishka import AsyncContainer, FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.core.events.sync import SyncRequested
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.faststream.jstream import stream

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
)
@inject
async def run_requested_sync(
    data: SyncRequested,
    container: FromDishka[AsyncContainer],
) -> None:
    interactor = await container.get(EXECUTORS[data.source])
    await interactor(run_id=data.sync_run_id)
