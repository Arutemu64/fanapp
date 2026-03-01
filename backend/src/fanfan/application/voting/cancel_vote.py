import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.gateways.votes import VoteGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.voting import DeletedVoteEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.exceptions.votes import VoteNotFound
from fanfan.core.services.voting import VotingService
from fanfan.core.vo.nomination import NominationId

logger = logging.getLogger(__name__)


class CancelVoteRequest(BaseModel):
    nomination_id: NominationId


class CancelVote:
    def __init__(
        self,
        vote_gateway: VoteGateway,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        id_provider: IdProvider,
        events_broker: EventBroker,
        service: VotingService,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.user_gateway = user_gateway
        self.vote_gateway = vote_gateway
        self.uow = uow
        self.id_provider = id_provider
        self.events_broker = events_broker
        self.service = service
        self.ticket_gateway = ticket_gateway

    async def __call__(self, data: CancelVoteRequest) -> None:
        # Ensure user can undo vote
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        ticket = await self.ticket_gateway.get_ticket_by_user_id(current_user.id)
        # TODO remove unnecessary check?
        await self.service.ensure_user_can_vote(user=current_user, ticket=ticket)

        async with self.uow:
            vote = await self.vote_gateway.get_user_vote_by_nomination(
                user_id=current_user.id,
                nomination_id=data.nomination_id,
            )
            if vote is None:
                raise VoteNotFound
            await self.vote_gateway.delete_vote(vote)
            await self.uow.commit()
            logger.info(
                "User %s cancelled their vote for %s",
                vote.user_id,
                vote.participant_id,
                extra={"vote": vote},
            )
            await self.events_broker.publish(
                DeletedVoteEvent(
                    vote_id=vote.id,
                    user_id=current_user.id,
                    participant_id=vote.participant_id,
                )
            )
