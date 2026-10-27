from datetime import datetime

from pydantic import BaseModel

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.voting import VotingService
from fanfan.core.vo.vote import VotingStatus


class GetVotingStatusOutput(BaseModel):
    can_vote: bool
    status: VotingStatus
    voting_start: datetime | None
    voting_end: datetime | None


class GetVotingStatus:
    def __init__(
        self,
        voting_service: VotingService,
        current_user_provider: CurrentUserProvider,
        ticket_gateway: TicketGateway,
    ) -> None:
        self.voting_service = voting_service
        self.current_user_provider = current_user_provider
        self.ticket_gateway = ticket_gateway

    async def __call__(self) -> GetVotingStatusOutput:
        current_user = await self.current_user_provider.get_user()
        if current_user is None:
            start, end = await self.voting_service.get_voting_window()
            return GetVotingStatusOutput(
                can_vote=False,
                status=VotingStatus.NOT_AUTHENTICATED,
                voting_start=start,
                voting_end=end,
            )
        ticket = await self.ticket_gateway.get_by_user_id(current_user.id)
        state = await self.voting_service.get_voting_state(current_user, ticket)
        return GetVotingStatusOutput(
            can_vote=state.status == VotingStatus.OPEN,
            status=state.status,
            voting_start=state.voting_start,
            voting_end=state.voting_end,
        )
