import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.tickets import TicketService
from fanfan.core.exceptions.tickets import (
    TicketNotFound,
)
from fanfan.core.vo.ticket import normalize_ticket_barcode

logger = logging.getLogger(__name__)


class LinkTicketInput(BaseModel):
    barcode: str


class LinkTicket:
    def __init__(
        self,
        ticket_gateway: TicketGateway,
        user_gateway: UserGateway,
        tickets_service: TicketService,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.ticket_gateway = ticket_gateway
        self.user_gateway = user_gateway
        self.tickets_service = tickets_service
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: LinkTicketInput) -> None:
        current_user = await self.current_user_provider.require_user()
        # Exact spelling first, so an imported vendor barcode is never rewritten
        # into a different one; the folded form only rescues a mistyped FAN- code.
        barcode = data.barcode.strip()
        ticket = await self.ticket_gateway.get_by_barcode(barcode=barcode)
        normalized = normalize_ticket_barcode(barcode)
        if ticket is None and normalized != barcode:
            ticket = await self.ticket_gateway.get_by_barcode(barcode=normalized)
        if ticket is None:
            raise TicketNotFound
        await self.tickets_service.link_ticket(ticket=ticket, user=current_user)
        await self.uow.commit()
        logger.info(
            "Ticket linked",
            extra={
                "ticket_id": str(ticket.id),
                "actor_id": str(current_user.id),
            },
        )
