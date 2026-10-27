from dataclasses import dataclass
from datetime import UTC, datetime

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.votes import VotingDisabled, VotingTicketRequired
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.vote import VotingStatus


@dataclass(frozen=True, slots=True)
class VotingState:
    status: VotingStatus
    voting_start: datetime | None
    voting_end: datetime | None


class VotingService:
    def __init__(self, settings_gateway: AppSettingsGateway) -> None:
        self.settings_gateway = settings_gateway

    async def get_voting_window(self) -> tuple[datetime | None, datetime | None]:
        settings = await self.settings_gateway.get()
        return settings.voting_start, settings.voting_end

    async def get_voting_state(self, user: User, ticket: Ticket | None) -> VotingState:
        settings = await self.settings_gateway.get()
        start, end = settings.voting_start, settings.voting_end
        if ticket is None or ticket.used_by_user_id != user.id:
            return VotingState(VotingStatus.NO_TICKET, start, end)
        if not settings.is_voting_open(now=datetime.now(UTC)):
            return VotingState(VotingStatus.DISABLED, start, end)
        return VotingState(VotingStatus.OPEN, start, end)

    async def ensure_user_can_vote(self, user: User, ticket: Ticket | None) -> None:
        state = await self.get_voting_state(user, ticket)
        if state.status is VotingStatus.NO_TICKET:
            raise VotingTicketRequired
        if state.status is VotingStatus.DISABLED:
            raise VotingDisabled
