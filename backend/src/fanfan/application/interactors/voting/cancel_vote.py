import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.exceptions.votes import VoteNotFound
from fanfan.core.vo.vote import VoteId

logger = logging.getLogger(__name__)


class CancelVoteInput(BaseModel):
    vote_id: VoteId


class CancelVote:
    def __init__(
        self,
        vote_gateway: VoteGateway,
        uow: UnitOfWork,
        vote_service: VotingService,
        current_user_provider: CurrentUserProvider,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.vote_gateway = vote_gateway
        self.uow = uow
        self.vote_service = vote_service
        self.current_user_provider = current_user_provider
        self.ticket_gateway = ticket_gateway

    async def __call__(self, data: CancelVoteInput) -> None:
        current_user = await self.current_user_provider.require_user()
        # Same gate as AddVote: once voting closes the ballot is final, so a
        # cancel cannot rewrite the tally or the prize-draw pool after the fact.
        # Checked before the vote lookup so the response says nothing about
        # whether the vote exists.
        ticket = await self.ticket_gateway.get_by_user_id(current_user.id)
        await self.vote_service.ensure_user_can_vote(user=current_user, ticket=ticket)

        vote = await self.vote_gateway.get(data.vote_id)
        # Treat a vote owned by someone else as missing so we don't leak its
        # existence to other users.
        if vote is None or vote.user_id != current_user.id:
            raise VoteNotFound
        await self.vote_gateway.delete(vote)
        await self.uow.commit()
        logger.info(
            "Vote cancelled",
            extra={
                "vote_id": str(vote.id),
                "actor_id": str(current_user.id),
                "participant_id": str(vote.participant_id),
            },
        )
