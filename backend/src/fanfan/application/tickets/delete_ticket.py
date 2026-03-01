import logging

from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.exceptions.tickets import TicketNotFound
from fanfan.core.vo.ticket import TicketId

logger = logging.getLogger(__name__)


class DeleteTicket:
    def __init__(self, ticket_gateway: TicketGateway, uow: UnitOfWork) -> None:
        self.ticket_gateway = ticket_gateway
        self.uow = uow

    async def __call__(self, ticket_id: TicketId) -> None:
        async with self.uow:
            ticket = await self.ticket_gateway.get_ticket_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFound
            await self.ticket_gateway.delete_ticket(ticket)
            await self.uow.commit()
            logger.info("Ticket %s was deleted", ticket_id, extra={"ticket": ticket})
            return
