import logging

from pydantic import BaseModel

from fanfan.application.dto.sync import SyncRunDTO
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.sync_run_tracker import SyncRunTracker
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncSource

logger = logging.getLogger(__name__)


class RequestSyncInput(BaseModel):
    source: SyncSource


class RequestSync:
    """Queue a sync for an organizer and hand back immediately.

    The actual work happens in the stream service (see ExecuteCosplaySync /
    ExecuteTicketsSync) — a full TicketsCloud sweep is unbounded and would
    outlive the HTTP request, and the API container is replaced on every deploy.
    """

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        tracker: SyncRunTracker,
        sync_run_gateway: SyncRunGateway,
        uow: UnitOfWork,
    ):
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.tracker = tracker
        self.sync_run_gateway = sync_run_gateway
        self.uow = uow

    async def __call__(self, data: RequestSyncInput) -> SyncRunDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        # Clear a run wedged by a dead worker first, otherwise the unique index
        # would report "already running" forever.
        await self.tracker.reap_stale(data.source)

        # Record SyncRequested on the run so it lands in the outbox in the same
        # transaction as the row — no dual write between commit and publish.
        run = SyncRun.create(source=data.source, by_user_id=current_user.id)
        run.queue()
        await self.sync_run_gateway.add(run)
        await self.uow.commit()

        logger.info(
            "Sync requested",
            extra={
                "sync_run_id": str(run.id),
                "source": run.source.value,
                "actor_id": str(current_user.id),
            },
        )
        return SyncRunDTO(
            id=run.id,
            source=run.source,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            result=run.result,
            error=run.error,
        )
