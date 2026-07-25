import logging

from fanfan.application.interactors.tickets.sync_tickets import SyncTickets
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.sync_run_tracker import (
    SYNC_FAILED_ERROR,
    SyncRunTracker,
)
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncRunId, SyncSource

logger = logging.getLogger(__name__)


class ExecuteTicketsSync:
    """Run a TicketsCloud sync and record it, for every trigger.

    Kept separate from ExecuteCosplaySync rather than dispatching on source in
    one interactor: Dishka resolves constructor dependencies eagerly, and the
    vendor config providers raise when their vendor is unset. A single
    interactor injecting both syncs would fail to resolve on a deployment that
    configures only one of the two — and both are independently optional.
    """

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        tracker: SyncRunTracker,
        sync_tickets: SyncTickets,
    ):
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.tracker = tracker
        self.sync_tickets = sync_tickets

    async def __call__(self, run_id: SyncRunId | None = None) -> None:
        # Under cron/CLI/NATS this resolves to the seeded system user, which is
        # granted sync:run by migration — the check is real, not decorative.
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        run = await self.tracker.start(SyncSource.TCLOUD, run_id, current_user.id)
        if run is None:
            return

        try:
            output = await self.sync_tickets()
        except Exception:
            # See ExecuteCosplaySync: recorded and logged, never re-raised.
            logger.exception(
                "TicketsCloud sync failed", extra={"sync_run_id": str(run.id)}
            )
            await self.tracker.fail(run, SYNC_FAILED_ERROR)
            return

        await self.tracker.finish(run, f"Новых билетов: {output.new_tickets_count}")
