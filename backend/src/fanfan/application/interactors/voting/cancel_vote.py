import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
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
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.vote_gateway = vote_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: CancelVoteInput) -> None:
        current_user = await self.current_user_provider.require_user()

        vote = await self.vote_gateway.get(data.vote_id)
        # Treat a vote owned by someone else as missing so we don't leak its
        # existence to other users.
        if vote is None or vote.user_id != current_user.id:
            raise VoteNotFound
        vote.delete()
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
