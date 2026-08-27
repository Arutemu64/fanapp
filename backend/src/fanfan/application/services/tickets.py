from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.exceptions.tickets import UserAlreadyHasTicketLinked
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User


class TicketService:
    def __init__(
        self,
        ticket_gateway: TicketGateway,
        user_gateway: UserGateway,
    ):
        self.ticket_gateway = ticket_gateway
        self.user_gateway = user_gateway

    async def link_ticket(self, ticket: Ticket, user: User):
        existing_ticket = await self.ticket_gateway.get_by_user_id(user.id)
        if existing_ticket:
            raise UserAlreadyHasTicketLinked

        user.set_role(ticket.role)
        await self.user_gateway.save(user)

        ticket.set_as_used(user.id)
        await self.ticket_gateway.save(ticket)
