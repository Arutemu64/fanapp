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

logger = logging.getLogger(__name__)


class LinkTicketInput(BaseModel):
    barcode: str


class LinkTicket:
    def __init__(
        self,
        ticket_repo: TicketGateway,
        user_repo: UserGateway,
        tickets_service: TicketService,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.ticket_repo = ticket_repo
        self.user_repo = user_repo
        self.tickets_service = tickets_service
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: LinkTicketInput) -> None:
        current_user = await self.current_user_provider.require_user()
        ticket = await self.ticket_repo.get_by_barcode(barcode=data.barcode)
        if ticket is None:
            raise TicketNotFound
        await self.tickets_service.link_ticket(ticket=ticket, user=current_user)
        await self.uow.commit()
        logger.info(
            "Ticket %s was linked to user %s",
            ticket.id,
            current_user.id,
        )
