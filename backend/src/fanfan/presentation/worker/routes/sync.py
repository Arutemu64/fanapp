from procrastinate import Blueprint

from fanfan.application.commands.sync import RunSyncCommand
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.worker.subscriber import Delivery, subscriber

sync_tasks = Blueprint()

# Resolved lazily by source rather than up front: Dishka resolves constructor
# dependencies eagerly, and each vendor's config provider raises when that
# vendor is unset, so asking for both here would break a deployment that
# configures only one.
EXECUTORS = {
    SyncSource.COSPLAY2: ExecuteCosplaySync,
    SyncSource.TCLOUD: ExecuteTicketsSync,
}


@subscriber(sync_tasks, RunSyncCommand, name="run_requested_sync")
async def run_requested_sync(command: RunSyncCommand, delivery: Delivery) -> None:
    interactor = await delivery.container.get(EXECUTORS[command.source])
    # A sync can run for minutes. The worker's heartbeat keeps the job from
    # being retried as stalled meanwhile; correctness does not rest on it: the
    # worker lock in SyncRunTracker.start() is what stops a second run.
    await interactor(run_id=command.sync_run_id)
