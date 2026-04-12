import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
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
        ticket_repo: TicketRepository,
        user_repo: UserRepository,
        tickets_service: TicketService,
        trx: TransactionManager,
        id_provider: IdProvider,
    ) -> None:
        self.ticket_repo = ticket_repo
        self.user_repo = user_repo
        self.tickets_service = tickets_service
        self.trx = trx
        self.id_provider = id_provider

    async def __call__(self, data: LinkTicketInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        ticket = await self.ticket_repo.get_by_barcode(barcode=data.barcode)
        if ticket is None:
            raise TicketNotFound
        await self.tickets_service.link_ticket(ticket=ticket, user=current_user)
        await self.trx.commit()
        logger.info(
            "Ticket %s was linked to user %s",
            ticket.id,
            current_user.id,
        )
