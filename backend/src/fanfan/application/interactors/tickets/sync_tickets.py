import logging

from pydantic import BaseModel

from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.tickets_import import TicketImportService

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
        uow: UnitOfWork,
    ):
        self.source = source
        self.ticket_import_service = ticket_import_service
        self.uow = uow

    async def __call__(self) -> SyncTicketsOutput:
        new_tickets_count, removed_tickets_count = 0, 0
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
        await self.uow.commit()
        # TODO: Find a way to correctly proceed refunds
        return SyncTicketsOutput(
            new_tickets_count=new_tickets_count,
            removed_tickets_count=removed_tickets_count,
        )
