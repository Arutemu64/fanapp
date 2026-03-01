from pydantic import BaseModel

from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.services.voting import VotingService
from fanfan.core.vo.vote import VotingStatus


class GetVotingStateResult(BaseModel):
    can_vote: bool
    status: VotingStatus


class GetVotingState:
    def __init__(
        self,
        voting_service: VotingService,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.user_gateway = user_gateway
        self.voting_service = voting_service
        self.id_provider = id_provider
        self.ticket_gateway = ticket_gateway

    async def __call__(self) -> GetVotingStateResult:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            return GetVotingStateResult(
                can_vote=False, status=VotingStatus.NOT_AUTHENTICATED
            )
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            return GetVotingStateResult(
                can_vote=False, status=VotingStatus.NOT_AUTHENTICATED
            )
        ticket = (
            await self.ticket_gateway.get_ticket_by_user_id(current_user.id)
            if current_user
            else None
        )
        status = await self.voting_service.get_voting_state(current_user, ticket)
        return GetVotingStateResult(can_vote=status == VotingStatus.OPEN, status=status)
