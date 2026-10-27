import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.tickets_import import TicketImportService

logger = logging.getLogger(__name__)


class ProcessTicketOrderInput(BaseModel):
    order_id: str


class ProcessTicketOrderOutput(BaseModel):
    new_tickets_count: int


class ProcessTicketOrder:
    def __init__(
        self,
        source: TicketsSource,
        app_settings_gateway: AppSettingsGateway,
        ticket_import_service: TicketImportService,
        uow: UnitOfWork,
    ) -> None:
        self.source = source
        self.app_settings_gateway = app_settings_gateway
        self.ticket_import_service = ticket_import_service
        self.uow = uow

    async def __call__(self, data: ProcessTicketOrderInput) -> ProcessTicketOrderOutput:
        tickets = await self.source.fetch_order_tickets(data.order_id)
        tickets_config = (await self.app_settings_gateway.get()).tickets
        new_tickets_count = 0
        for external in tickets:
            role = tickets_config.role_for_tcloud_event(external.event_id)
            if await self.ticket_import_service.import_ticket(external, role=role):
                new_tickets_count += 1
        await self.uow.commit()
        logger.info(
            "TicketsCloud order processed",
            extra={"order_id": data.order_id, "new_tickets": new_tickets_count},
        )
        return ProcessTicketOrderOutput(new_tickets_count=new_tickets_count)
