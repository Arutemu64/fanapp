import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.tickets import TicketNotLinked
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class UnlinkUserTicketInput(BaseModel):
    user_id: UserId


class UnlinkUserTicketOutput(BaseModel):
    deleted_votes: int


class UnlinkUserTicket:
    """An organiser takes a ticket off a user (users:manage).

    The ticket is freed for linking again. A ticket is what entitles a vote, so
    the user's votes go with it — they leave the tally and the prize-draw pool.
    The role stays as it is: it may have been set by hand since the ticket was
    linked, so the organiser changes it separately if it should go too.
    """

    def __init__(
        self,
        ticket_gateway: TicketGateway,
        vote_gateway: VoteGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.ticket_gateway = ticket_gateway
        self.vote_gateway = vote_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: UnlinkUserTicketInput) -> UnlinkUserTicketOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_MANAGE
        )

        ticket = await self.ticket_gateway.get_by_user_id(data.user_id)
        if ticket is None:
            raise TicketNotLinked
        ticket.release()
        await self.ticket_gateway.save(ticket)
        deleted_votes = await self.vote_gateway.delete_all_by_user(data.user_id)
        await self.uow.commit()
        logger.info(
            "Ticket unlinked",
            extra={
                "ticket_id": str(ticket.id),
                "user_id": str(data.user_id),
                "actor_id": str(current_user.id),
                "deleted_votes": deleted_votes,
            },
        )
        return UnlinkUserTicketOutput(deleted_votes=deleted_votes)
