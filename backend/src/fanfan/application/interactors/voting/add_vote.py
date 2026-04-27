import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.participants import ParticipantRepository
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.repositories.votes import VoteRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.events.voting import CreatedVoteEvent
from fanfan.core.models.vote import Vote
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.vote import VoteId

logger = logging.getLogger(__name__)


class AddVoteInput(BaseModel):
    participant_id: ParticipantId


class AddVoteOutput(BaseModel):
    vote_id: VoteId


class AddVote:
    def __init__(
        self,
        participant_repo: ParticipantRepository,
        user_repo: UserRepository,
        vote_repo: VoteRepository,
        trx: TransactionManager,
        vote_service: VotingService,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        ticket_repo: TicketRepository,
    ) -> None:
        self.participant_repo = participant_repo
        self.user_repo = user_repo
        self.vote_repo = vote_repo
        self.trx = trx
        self.vote_service = vote_service
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker
        self.ticket_repo = ticket_repo

    async def __call__(
        self,
        data: AddVoteInput,
    ) -> AddVoteOutput:
        current_user = await self.current_user_provider.require_user()
        ticket = await self.ticket_repo.get_by_user_id(current_user.id)
        await self.vote_service.ensure_user_can_vote(user=current_user, ticket=ticket)

        vote = Vote(user_id=current_user.id, participant_id=data.participant_id)
        await self.vote_repo.add(vote)
        await self.trx.commit()

        logger.info(
            "User %s voted for participant %s",
            current_user.id,
            data.participant_id,
        )
        await self.events_broker.publish(
            CreatedVoteEvent(
                vote_id=vote.id,
                user_id=vote.user_id,
                participant_id=vote.participant_id,
            )
        )
        return AddVoteOutput(vote_id=vote.id)
