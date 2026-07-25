import logging

from fanfan.application.interactors.cosplay.sync_cosplay import SyncCosplay
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.sync_run_tracker import (
    SYNC_FAILED_ERROR,
    SyncRunTracker,
)
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncRunId, SyncSource

logger = logging.getLogger(__name__)


class ExecuteCosplaySync:
    """Run a Cosplay2 sync and record it, for every trigger.

    Cron, the CLI and the NATS consumer all go through here rather than calling
    SyncCosplay directly, so every run leaves an audit row and takes part in the
    one-active-run-per-source guard.
    """

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        tracker: SyncRunTracker,
        sync_cosplay: SyncCosplay,
    ):
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.tracker = tracker
        self.sync_cosplay = sync_cosplay

    async def __call__(self, run_id: SyncRunId | None = None) -> None:
        # Under cron/CLI/NATS this resolves to the seeded system user, which is
        # granted sync:run by migration — the check is real, not decorative.
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        run = await self.tracker.start(SyncSource.COSPLAY2, run_id, current_user.id)
        if run is None:
            return

        try:
            output = await self.sync_cosplay()
        except Exception:
            # Recorded on the run and logged (Sentry picks ERROR logs up), but
            # deliberately not re-raised: the NATS consumer would redeliver and
            # retry forever against a vendor that is simply down.
            logger.exception("Cosplay2 sync failed", extra={"sync_run_id": str(run.id)})
            await self.tracker.fail(run, SYNC_FAILED_ERROR)
            return

        await self.tracker.finish(
            run,
            f"Номинаций: {output.nominations_count}, "
            f"участников: {output.participants_count}",
        )
