import logging
from datetime import UTC, datetime, timedelta

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.ports.worker_lock import WorkerLock
from fanfan.core.exceptions.sync import SyncAlreadyRunning
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

STALE_RUN_TIMEOUT = timedelta(minutes=30)
STALE_RUN_ERROR = "Синхронизация прервалась — процесс не ответил вовремя"

SYNC_FAILED_ERROR = "Не удалось синхронизировать — попробуй ещё раз позже"


def sync_lock_key(source: SyncSource) -> str:
    return f"sync:{source.value}"


class SyncRunTracker:
    """Owns the SyncRun lifecycle for every trigger (HTTP, cron, CLI).

    Deliberately does not authorize: its callers do, and it takes an already
    authenticated ``by_user_id`` rather than reaching for CurrentUserProvider,
    so there is exactly one authorization site per run.
    """

    def __init__(
        self,
        sync_run_gateway: SyncRunGateway,
        uow: UnitOfWork,
        realtime: RealtimeGateway,
        worker_lock: WorkerLock,
    ) -> None:
        self.sync_run_gateway = sync_run_gateway
        self.uow = uow
        self.realtime = realtime
        self.worker_lock = worker_lock

    async def reap_stale(self, source: SyncSource) -> None:
        """Fail runs whose worker is gone, for a caller that will not run the sync."""
        if not await self.worker_lock.try_acquire(sync_lock_key(source)):
            return
        try:
            await self._reap_stale(source)
        finally:
            await self.worker_lock.release()

    async def _reap_stale(self, source: SyncSource) -> None:
        cutoff = datetime.now(UTC) - STALE_RUN_TIMEOUT
        reaped = await self.sync_run_gateway.fail_stale(
            source, older_than=cutoff, error=STALE_RUN_ERROR
        )
        if reaped:
            await self.uow.commit()
            logger.warning(
                "Reaped stale sync runs",
                extra={"source": source.value, "reaped": reaped},
            )

    async def start(
        self,
        source: SyncSource,
        run_id: SyncRunId | None,
        by_user_id: UserId,
    ) -> SyncRun | None:
        """Move a run into RUNNING, or return None if the sync should be skipped.

        ``run_id`` is set on the manual path, where RequestSync already created a
        PENDING row; it is None for cron and CLI, which create their own row here
        so that unattended runs are recorded too.

        The source's lock is held from here until ``finish``/``fail``; a
        trigger that is skipped, or raises before the run starts, gives it back
        at once.
        """
        if not await self.worker_lock.try_acquire(sync_lock_key(source)):
            if run_id is None:
                logger.info(
                    "Sync already running, skipping this trigger",
                    extra={"source": source.value},
                )
                return None
            raise SyncAlreadyRunning

        run: SyncRun | None = None
        try:
            run = await self._start_holding_lock(source, run_id, by_user_id)
        finally:
            if run is None:
                await self.worker_lock.release()
        return run

    async def _start_holding_lock(
        self,
        source: SyncSource,
        run_id: SyncRunId | None,
        by_user_id: UserId,
    ) -> SyncRun | None:
        await self._reap_stale(source)

        if run_id is None:
            run = SyncRun.create(source=source, by_user_id=by_user_id)
            try:
                await self.sync_run_gateway.add(run)
            except SyncAlreadyRunning:
                await self.uow.rollback()
                logger.info(
                    "Sync already running, skipping this trigger",
                    extra={"source": source.value},
                )
                return None
        else:
            run = await self.sync_run_gateway.get(run_id)
            if run is None:
                logger.warning(
                    "Sync run vanished before it could start",
                    extra={"sync_run_id": str(run_id)},
                )
                return None
            if run.status in (SyncRunStatus.FINISHED, SyncRunStatus.FAILED):
                logger.info(
                    "Sync run already settled, skipping redelivered trigger",
                    extra={"sync_run_id": str(run_id), "status": run.status.value},
                )
                return None
            if run.status is SyncRunStatus.RUNNING:
                logger.warning(
                    "Resuming interrupted sync run",
                    extra={"sync_run_id": str(run_id)},
                )

        run.mark_running(datetime.now(UTC))
        await self.sync_run_gateway.save(run)
        await self.uow.commit()
        await self._publish(run)
        return run

    async def finish(self, run: SyncRun, result: str) -> None:
        run.mark_finished(result, datetime.now(UTC))
        await self._persist(run)
        await self.worker_lock.release()
        logger.info(
            "Sync finished",
            extra={"sync_run_id": str(run.id), "source": run.source.value},
        )

    async def fail(self, run: SyncRun, error: str) -> None:
        await self.uow.rollback()
        run.mark_failed(error, datetime.now(UTC))
        await self._persist(run)
        await self.worker_lock.release()
        logger.warning(
            "Sync failed",
            extra={"sync_run_id": str(run.id), "source": run.source.value},
        )

    async def _persist(self, run: SyncRun) -> None:
        await self.sync_run_gateway.save(run)
        await self.uow.commit()
        await self._publish(run)

    async def _publish(self, run: SyncRun) -> None:
        await self.realtime.publish(
            SSEMessage(
                event_name=SSEEventName.SYNC_RUN_UPDATED,
                data={"source": run.source.value, "status": run.status.value},
            )
        )
