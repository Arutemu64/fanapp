import logging

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.tickets import (
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.tickets import TicketService

logger = logging.getLogger(__name__)


class LinkTicketCommand(BaseModel):
    barcode: str


class LinkTicket:
    def __init__(
        self,
        ticket_gateway: TicketGateway,
        user_gateway: UserGateway,
        tickets_service: TicketService,
        uow: UnitOfWork,
        id_provider: IdProvider,
    ) -> None:
        self.ticket_gateway = ticket_gateway
        self.user_gateway = user_gateway
        self.tickets_service = tickets_service
        self.uow = uow
        self.id_provider = id_provider

    async def __call__(self, data: LinkTicketCommand) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            ticket = await self.ticket_gateway.get_ticket_by_barcode(
                barcode=data.barcode
            )
            if ticket is None:
                raise TicketNotFound
            try:
                await self.tickets_service.link_ticket(ticket=ticket, user=current_user)
                await self.uow.commit()
            except (IntegrityError, UserAlreadyHasTicketLinked):
                await self.uow.rollback()
                raise
            else:
                logger.info(
                    "Ticket %s was linked to user %s",
                    ticket.id,
                    current_user.id,
                    extra={"user": current_user, "ticket": ticket},
                )
