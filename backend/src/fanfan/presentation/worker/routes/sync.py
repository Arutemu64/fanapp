from dishka import AsyncContainer

from fanfan.application.dto.jobs import Job
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.core.events.sync import SyncRequested
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.worker.router import JobRouter

sync_router = JobRouter()

# Resolved by source rather than both up front: each vendor's config provider
# raises when that vendor is unset, so asking for both would break a deployment
# that configures only one.
EXECUTORS = {
    SyncSource.COSPLAY2: ExecuteCosplaySync,
    SyncSource.TCLOUD: ExecuteTicketsSync,
}


@sync_router.handler(SyncRequested, name="run_requested_sync")
async def run_requested_sync(
    event: SyncRequested, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(EXECUTORS[event.source])
    # The worker renews the job's lease while the sync runs, but correctness
    # does not rest on it: the worker lock in SyncRunTracker.start() is what
    # stops a second worker running it.
    await interactor(run_id=event.sync_run_id)
