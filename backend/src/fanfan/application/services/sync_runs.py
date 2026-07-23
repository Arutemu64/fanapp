import logging
from datetime import UTC, datetime

from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import (
    SyncRunStatus,
    SyncSource,
    SyncTrigger,
    generate_sync_run_id,
)

logger = logging.getLogger(__name__)


class SyncRunRecorderService:
    """Persists the outcome of a sync run into the append-only run log.

    Shared by the Cosplay2 and TicketsCloud sync interactors so both feed the
    same audit trail behind the manual-sync page.
    """

    def __init__(
        self,
        sync_run_gateway: SyncRunGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.sync_run_gateway = sync_run_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def record_completed(
        self,
        source: SyncSource,
        trigger: SyncTrigger,
        started_at: datetime,
    ) -> None:
        """Add a completed run row and commit.

        The caller must NOT have committed its final batch yet: the commit here
        covers the sync's pending changes and the run row atomically.
        """
        await self._record(
            source=source,
            trigger=trigger,
            status=SyncRunStatus.COMPLETED,
            started_at=started_at,
            error_message=None,
        )

    async def record_failed(
        self,
        source: SyncSource,
        trigger: SyncTrigger,
        started_at: datetime,
        error_message: str,
    ) -> None:
        # Discard whatever the failed sync left pending (the session may also be
        # in an aborted state after a DB error) so the run row can be written in
        # a clean transaction of its own.
        await self.uow.rollback()
        await self._record(
            source=source,
            trigger=trigger,
            status=SyncRunStatus.FAILED,
            started_at=started_at,
            error_message=error_message,
        )

    async def _record(
        self,
        *,
        source: SyncSource,
        trigger: SyncTrigger,
        status: SyncRunStatus,
        started_at: datetime,
        error_message: str | None,
    ) -> None:
        # Real user for web-triggered runs; the system identity (scheduler/CLI)
        # resolves to no user and is recorded as None — the trigger field is
        # what attributes those runs.
        current_user = await self.current_user_provider.get_user()
        run = SyncRun(
            id=generate_sync_run_id(),
            source=source,
            trigger=trigger,
            status=status,
            started_by_user_id=current_user.id if current_user else None,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            error_message=error_message,
        )
        await self.sync_run_gateway.add(run)
        await self.uow.commit()
        logger.info(
            "Sync run recorded",
            extra={
                "sync_run_id": str(run.id),
                "source": source.value,
                "trigger": trigger.value,
                "status": status.value,
            },
        )
