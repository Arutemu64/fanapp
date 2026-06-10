import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.exceptions.votes import VoteNotFound
from fanfan.core.vo.nomination import NominationId

logger = logging.getLogger(__name__)


class CancelVoteByNominationInput(BaseModel):
    nomination_id: NominationId


class CancelVoteByNomination:
    def __init__(
        self,
        vote_gateway: VoteGateway,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
        service: VotingService,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.user_gateway = user_gateway
        self.vote_gateway = vote_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider
        self.service = service
        self.ticket_gateway = ticket_gateway

    async def __call__(self, data: CancelVoteByNominationInput) -> None:
        current_user = await self.current_user_provider.require_user()
        ticket = await self.ticket_gateway.get_by_user_id(current_user.id)
        # TODO remove unnecessary check?
        await self.service.ensure_user_can_vote(user=current_user, ticket=ticket)

        vote = await self.vote_gateway.get_user_vote_by_nomination(
            nomination_id=data.nomination_id, user_id=current_user.id
        )
        if vote is None:
            raise VoteNotFound
        vote.delete()
        await self.vote_gateway.delete(vote)
        await self.uow.commit()
        logger.info(
            "User %s cancelled their vote for %s",
            vote.user_id,
            vote.participant_id,
        )
