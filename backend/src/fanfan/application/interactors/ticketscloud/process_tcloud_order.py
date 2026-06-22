import logging

from pydantic import BaseModel

from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.tickets_import import TicketImportService

logger = logging.getLogger(__name__)


class ProcessTCloudOrderInput(BaseModel):
    order_id: str


class ProcessTCloudOrderOutput(BaseModel):
    new_tickets_count: int


class ProcessTCloudOrder:
    def __init__(
        self,
        source: TicketsSource,
        ticket_import_service: TicketImportService,
        uow: UnitOfWork,
    ):
        self.source = source
        self.ticket_import_service = ticket_import_service
        self.uow = uow

    async def __call__(self, data: ProcessTCloudOrderInput) -> ProcessTCloudOrderOutput:
        # The webhook body is untrusted, so the source re-fetches the
        # authoritative order from the authenticated API by id.
        tickets = await self.source.fetch_order_tickets(data.order_id)
        new_tickets_count = 0
        for external in tickets:
            if await self.ticket_import_service.import_ticket(external):
                new_tickets_count += 1
        await self.uow.commit()
        logger.info(
            "TicketsCloud order processed",
            extra={"order_id": data.order_id, "new_tickets": new_tickets_count},
        )
        return ProcessTCloudOrderOutput(new_tickets_count=new_tickets_count)
