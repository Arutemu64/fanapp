import logging
from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.sync_runs import SyncRunRecorderService
from fanfan.application.services.tickets_import import TicketImportService
from fanfan.core.vo.sync import SyncSource, SyncTrigger

logger = logging.getLogger(__name__)

# Commit periodically during a full sync so a large run is not held in one giant
# transaction and progress is persisted incrementally.
COMMIT_BATCH_SIZE = 200


class SyncTicketsOutput(BaseModel):
    new_tickets_count: int
    removed_tickets_count: int


class SyncTickets:
    def __init__(
        self,
        source: TicketsSource,
        ticket_import_service: TicketImportService,
        run_recorder: SyncRunRecorderService,
        uow: UnitOfWork,
    ):
        self.source = source
        self.ticket_import_service = ticket_import_service
        self.run_recorder = run_recorder
        self.uow = uow

    async def __call__(
        self, trigger: SyncTrigger = SyncTrigger.SCHEDULE
    ) -> SyncTicketsOutput:
        started_at = datetime.now(UTC)
        try:
            new_tickets_count = await self._import_tickets()
        except Exception as exc:
            try:
                await self.run_recorder.record_failed(
                    source=SyncSource.TICKETSCLOUD,
                    trigger=trigger,
                    started_at=started_at,
                    error_message=str(exc),
                )
            except Exception:
                # Never mask the sync failure with a bookkeeping failure.
                logger.exception("Failed to record failed TicketsCloud sync run")
            raise
        # Commits the last import batch and the run row atomically.
        await self.run_recorder.record_completed(
            source=SyncSource.TICKETSCLOUD,
            trigger=trigger,
            started_at=started_at,
        )
        # TODO Find a way to correctly proceed refunds
        return SyncTicketsOutput(
            new_tickets_count=new_tickets_count,
            removed_tickets_count=0,
        )

    async def _import_tickets(self) -> int:
        new_tickets_count = 0
        seen_since_commit = 0
        async for external in self.source.fetch_all_tickets():
            if await self.ticket_import_service.import_ticket(external):
                new_tickets_count += 1
            seen_since_commit += 1
            if seen_since_commit >= COMMIT_BATCH_SIZE:
                await self.uow.commit()
                seen_since_commit = 0
                logger.info(
                    "TicketsCloud sync progress",
                    extra={"new_tickets": new_tickets_count},
                )
        return new_tickets_count
