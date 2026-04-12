from pydantic import BaseModel

from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.tickets import TicketRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.services.voting import VotingService
from fanfan.core.vo.vote import VotingStatus


class GetVotingStateOutput(BaseModel):
    can_vote: bool
    status: VotingStatus


class GetVotingState:
    def __init__(
        self,
        voting_service: VotingService,
        user_repo: UserRepository,
        id_provider: IdProvider,
        ticket_repo: TicketRepository,
    ) -> None:
        self.user_repo = user_repo
        self.voting_service = voting_service
        self.id_provider = id_provider
        self.ticket_repo = ticket_repo

    async def __call__(self) -> GetVotingStateOutput:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            return GetVotingStateOutput(
                can_vote=False, status=VotingStatus.NOT_AUTHENTICATED
            )
        current_user = await self.user_repo.get_by_id(current_user_id)
        if current_user is None:
            return GetVotingStateOutput(
                can_vote=False, status=VotingStatus.NOT_AUTHENTICATED
            )
        ticket = (
            await self.ticket_repo.get_by_user_id(current_user.id)
            if current_user
            else None
        )
        status = await self.voting_service.get_voting_state(current_user, ticket)
        return GetVotingStateOutput(can_vote=status == VotingStatus.OPEN, status=status)
