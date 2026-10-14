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
    revoked_tickets_count: int


class SyncTickets:
    def __init__(
        self,
        source: TicketsSource,
        ticket_import_service: TicketImportService,
        uow: UnitOfWork,
    ) -> None:
        self.source = source
        self.ticket_import_service = ticket_import_service
        self.uow = uow

    async def __call__(self) -> SyncTicketsOutput:
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
        await self.uow.commit()

        # Revoke after importing: the import pass fills in the order id on rows
        # stored before it was tracked, so revocation can match them exactly.
        revoked_tickets_count = 0
        seen_since_commit = 0
        async for revoked in self.source.fetch_revoked_tickets():
            if await self.ticket_import_service.revoke_ticket(revoked):
                revoked_tickets_count += 1
            seen_since_commit += 1
            if seen_since_commit >= COMMIT_BATCH_SIZE:
                await self.uow.commit()
                seen_since_commit = 0
        await self.uow.commit()

        return SyncTicketsOutput(
            new_tickets_count=new_tickets_count,
            revoked_tickets_count=revoked_tickets_count,
        )
