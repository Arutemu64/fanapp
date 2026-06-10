import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import VoteAlreadyExists
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
        participant_repo: ParticipantGateway,
        vote_repo: VoteGateway,
        uow: UnitOfWork,
        vote_service: VotingService,
        current_user_provider: CurrentUserProvider,
        ticket_repo: TicketGateway,
    ) -> None:
        self.participant_repo = participant_repo
        self.vote_repo = vote_repo
        self.uow = uow
        self.vote_service = vote_service
        self.current_user_provider = current_user_provider
        self.ticket_repo = ticket_repo

    async def __call__(
        self,
        data: AddVoteInput,
    ) -> AddVoteOutput:
        current_user = await self.current_user_provider.require_user()
        ticket = await self.ticket_repo.get_by_user_id(current_user.id)
        await self.vote_service.ensure_user_can_vote(user=current_user, ticket=ticket)

        # User can only vote once in a nomination
        participant = await self.participant_repo.get(data.participant_id)
        if participant is None:
            raise ParticipantNotFound
        if await self.vote_repo.get_user_vote_by_nomination(
            nomination_id=participant.nomination_id, user_id=current_user.id
        ):
            raise VoteAlreadyExists

        vote = Vote.create(
            user_id=current_user.id,
            participant_id=data.participant_id,
        )
        await self.vote_repo.add(vote)
        await self.uow.commit()

        logger.info(
            "User %s voted for participant %s",
            current_user.id,
            data.participant_id,
        )
        return AddVoteOutput(vote_id=vote.id)
