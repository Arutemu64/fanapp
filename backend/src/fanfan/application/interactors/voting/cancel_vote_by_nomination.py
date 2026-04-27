import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.repositories.votes import VoteRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.events.voting import DeletedVoteEvent
from fanfan.core.exceptions.votes import VoteNotFound
from fanfan.core.vo.nomination import NominationId

logger = logging.getLogger(__name__)


class CancelUserVoteByNominationInput(BaseModel):
    nomination_id: NominationId


class CancelUserVoteByNomination:
    def __init__(
        self,
        vote_repo: VoteRepository,
        user_repo: UserRepository,
        trx: TransactionManager,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        service: VotingService,
        ticket_repo: TicketRepository,
    ) -> None:
        self.user_repo = user_repo
        self.vote_repo = vote_repo
        self.uow = trx
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker
        self.service = service
        self.ticket_repo = ticket_repo

    async def __call__(self, data: CancelUserVoteByNominationInput) -> None:
        current_user = await self.current_user_provider.require_user()
        ticket = await self.ticket_repo.get_by_user_id(current_user.id)
        # TODO remove unnecessary check?
        await self.service.ensure_user_can_vote(user=current_user, ticket=ticket)

        vote = await self.vote_repo.get_user_vote_by_nomination_id(
            nomination_id=data.nomination_id,
            user_id=current_user.id,
        )
        if vote is None:
            raise VoteNotFound
        await self.vote_repo.delete(vote)
        await self.uow.commit()
        logger.info(
            "User %s cancelled their vote for %s",
            vote.user_id,
            vote.participant_id,
        )
        await self.events_broker.publish(
            DeletedVoteEvent(
                vote_id=vote.id,
                user_id=current_user.id,
                participant_id=vote.participant_id,
            )
        )
