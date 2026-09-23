import logging
from datetime import UTC, datetime, timedelta

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.run_lease import RunLease
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.sync import SyncAlreadyRunning
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

# How long an active run may go without finishing before it is treated as dead.
# A worker killed mid-run leaves its row with finished_at NULL, which the
# uq_sync_runs_active index then holds against every future run for that source
# — syncing would stop permanently. A live worker is never reaped however long
# it runs: reaping needs the source's lease, which that worker holds. So this
# only bounds how long a dead run, or a requested one whose trigger never
# arrived, blocks the source.
STALE_RUN_TIMEOUT = timedelta(minutes=30)
STALE_RUN_ERROR = "Синхронизация прервалась — процесс не ответил вовремя"

# Shown to the organizer when a sync raises. Deliberately generic: the real
# cause is in the logs and Sentry, and vendor errors are not actionable copy.
SYNC_FAILED_ERROR = "Не удалось синхронизировать — попробуй ещё раз позже"


def sync_lease_key(source: SyncSource) -> str:
    # One lease per source, not per run: the reaper has to know whether any
    # worker is still sweeping the source, whichever run it is on.
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
        lease: RunLease,
    ) -> None:
        self.sync_run_gateway = sync_run_gateway
        self.uow = uow
        self.realtime = realtime
        self.lease = lease

    async def reap_stale(self, source: SyncSource) -> None:
        """Fail runs whose worker is gone, for a caller that will not run the sync."""
        if not await self.lease.try_acquire(sync_lease_key(source)):
            # A live worker holds the lease, so its run is not stale however
            # old it is.
            return
        try:
            await self._reap_stale(source)
        finally:
            await self.lease.release()

    async def _reap_stale(self, source: SyncSource) -> None:
        # Caller holds the source's lease: only then is an old active row
        # proof of a dead worker rather than a slow one.
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

        The source's lease is held from here until ``finish``/``fail``; a
        trigger that is skipped, or raises before the run starts, gives it back
        at once.
        """
        if not await self.lease.try_acquire(sync_lease_key(source)):
            if run_id is None:
                # Another worker is mid-sweep: skip quietly, for the same reason
                # as the unique-index collision below.
                logger.info(
                    "Sync already running, skipping this trigger",
                    extra={"source": source.value},
                )
                return None
            # Redelivery alone does not prove the previous worker stopped: one
            # that missed its NATS heartbeats may still be running. The lease
            # does — a live worker holds it — so without it, back off and let
            # the trigger come again (the consumer redelivers on this error).
            raise SyncAlreadyRunning

        run: SyncRun | None = None
        try:
            run = await self._start_holding_lease(source, run_id, by_user_id)
        finally:
            if run is None:
                await self.lease.release()
        return run

    async def _start_holding_lease(
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
                # A scheduled tick colliding with a manual run is normal, not an
                # error — raising here would put Sentry noise on every overlap.
                # The manual path surfaces its own 409 from RequestSync instead.
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
            # The trigger is redelivered after an error or a dead worker. A
            # finished or failed run is done, so its trigger is a duplicate.
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
        await self.lease.release()
        logger.info(
            "Sync finished",
            extra={"sync_run_id": str(run.id), "source": run.source.value},
        )

    async def fail(self, run: SyncRun, error: str) -> None:
        # Always reached after the sync raised, which may have left the session
        # in a rollback-required state (e.g. a failed flush on a duplicate key).
        # Discard that poisoned transaction before writing the FAILED row —
        # otherwise _persist raises PendingRollbackError, the row stays RUNNING,
        # and the run is stuck "syncing" until reap_stale clears it 30 min later.
        await self.uow.rollback()
        run.mark_failed(error, datetime.now(UTC))
        await self._persist(run)
        await self.lease.release()
        logger.warning(
            "Sync failed",
            extra={"sync_run_id": str(run.id), "source": run.source.value},
        )

    async def _persist(self, run: SyncRun) -> None:
        await self.sync_run_gateway.save(run)
        await self.uow.commit()
        await self._publish(run)

    async def _publish(self, run: SyncRun) -> None:
        # Broadcast rather than target a user: the run is shared state, and any
        # organizer with the permission may be watching the page.
        await self.realtime.publish(
            SSEMessage(
                event_name=SSEEventName.SYNC_RUN_UPDATED,
                data={"source": run.source.value, "status": run.status.value},
            )
        )
