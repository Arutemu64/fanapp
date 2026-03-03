import logging

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.participants import ParticipantGateway
from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.gateways.votes import VoteGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.constraints import get_constraint_name
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.vote import VoteBaseDTO
from fanfan.core.events.voting import CreatedVoteEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.exceptions.votes import (
    AlreadyVotedInThisNomination,
)
from fanfan.core.models.vote import Vote
from fanfan.core.services.voting import VotingService
from fanfan.core.vo.participant import ParticipantId

logger = logging.getLogger(__name__)


class AddVoteCommand(BaseModel):
    participant_id: ParticipantId


class AddVote:
    def __init__(
        self,
        participant_gateway: ParticipantGateway,
        user_gateway: UserGateway,
        vote_gateway: VoteGateway,
        uow: UnitOfWork,
        vote_service: VotingService,
        id_provider: IdProvider,
        events_broker: EventBroker,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.participant_gateway = participant_gateway
        self.user_gateway = user_gateway
        self.vote_gateway = vote_gateway
        self.uow = uow
        self.vote_service = vote_service
        self.id_provider = id_provider
        self.events_broker = events_broker
        self.ticket_gateway = ticket_gateway

    async def __call__(
        self,
        data: AddVoteCommand,
    ) -> VoteBaseDTO:
        # Ensure user can even vote
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        ticket = await self.ticket_gateway.get_ticket_by_user_id(current_user.id)
        await self.vote_service.ensure_user_can_vote(user=current_user, ticket=ticket)

        async with self.uow:
            try:
                vote = Vote(user_id=current_user.id, participant_id=data.participant_id)
                await self.vote_gateway.add_vote(vote)
                await self.uow.commit()
            except IntegrityError as e:
                await self.uow.rollback()
                constraint_name = get_constraint_name(e)
                if constraint_name == "fk_votes_participant_id_participants":
                    raise ParticipantNotFound from e
                if constraint_name == "uq_votes_user_id":
                    raise AlreadyVotedInThisNomination from e
                raise
            else:
                logger.info(
                    "User %s voted for participant %s",
                    current_user.id,
                    data.participant_id,
                    extra={"vote": vote},
                )
                await self.events_broker.publish(
                    CreatedVoteEvent(
                        vote_id=vote.id,
                        user_id=vote.user_id,
                        participant_id=vote.participant_id,
                    )
                )
                return await self.vote_gateway.read_base_vote(vote.id)
