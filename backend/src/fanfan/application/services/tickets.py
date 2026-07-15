from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.core.exceptions.tickets import UserAlreadyHasTicketLinked
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.user_flag import UserFlagName


class TicketService:
    def __init__(
        self,
        ticket_gateway: TicketGateway,
        user_gateway: UserGateway,
        vote_gateway: VoteGateway,
        flag_gateway: UserFlagGateway,
    ):
        self.ticket_gateway = ticket_gateway
        self.user_gateway = user_gateway
        self.vote_gateway = vote_gateway
        self.flag_gateway = flag_gateway

    async def link_ticket(self, ticket: Ticket, user: User):
        existing_ticket = await self.ticket_gateway.get_by_user_id(user.id)
        if existing_ticket:
            raise UserAlreadyHasTicketLinked

        user.set_role(ticket.role)
        await self.user_gateway.save(user)

        ticket.set_as_used(user.id)
        await self.ticket_gateway.save(ticket)

    async def unlink_ticket(self, ticket: Ticket):
        if user_id := ticket.unlink():
            user = await self.user_gateway.get_by_id(user_id)
            if user is None:
                raise UserNotFound

            user.reset_ticket_role()
            await self.user_gateway.save(user)

            # Persist the ticket unlink before removing dependent voting data.
            await self.ticket_gateway.save(ticket)

            await self.vote_gateway.delete_all_user_votes(user_id)
            contest_flag = await self.flag_gateway.get_by_user(
                user_id=user_id, flag_name=UserFlagName.VOTING_CONTEST
            )
            if contest_flag:
                await self.flag_gateway.delete(contest_flag)
