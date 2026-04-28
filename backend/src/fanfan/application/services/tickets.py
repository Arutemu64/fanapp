from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.user_flags import UserFlagRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.repositories.votes import VoteRepository
from fanfan.core.constants.flags import VOTING_CONTEST_FLAG_NAME
from fanfan.core.exceptions.tickets import UserAlreadyHasTicketLinked
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User


class TicketService:
    def __init__(
        self,
        ticket_repo: TicketRepository,
        user_repo: UserRepository,
        vote_repo: VoteRepository,
        flag_repo: UserFlagRepository,
    ):
        self.ticket_repo = ticket_repo
        self.user_repo = user_repo
        self.vote_repo = vote_repo
        self.flag_repo = flag_repo

    async def link_ticket(self, ticket: Ticket, user: User):
        # Check if user got ticket linked already
        existing_ticket = await self.ticket_repo.get_by_user_id(user.id)
        if existing_ticket:
            raise UserAlreadyHasTicketLinked

        # Apply ticket role to user
        user.set_role(ticket.role)
        await self.user_repo.save(user)

        # Mark as used
        ticket.set_as_used(user.id)
        await self.ticket_repo.save(ticket)

    async def unlink_ticket(self, ticket: Ticket):
        if user_id := ticket.unlink():
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                raise UserNotFound

            # Reset user role
            user.reset_ticket_role()
            await self.user_repo.save(user)

            # Persist the ticket unlink before removing dependent voting data.
            await self.ticket_repo.save(ticket)

            # Delete user votes and contest flag
            await self.vote_repo.delete_all_user_votes(user_id)
            contest_flag = await self.flag_repo.get_by_user(
                user_id=user_id, flag_name=VOTING_CONTEST_FLAG_NAME
            )
            if contest_flag:
                await self.flag_repo.delete(contest_flag)
