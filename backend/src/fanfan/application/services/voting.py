from dataclasses import dataclass
from datetime import UTC, datetime

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.vote import VotingStatus


@dataclass(frozen=True, slots=True)
class VotingState:
    status: VotingStatus
    # The configured window, surfaced alongside the status so the client can
    # schedule its banner to flip exactly when the clock crosses a boundary
    # (there is no server event for that). None/None means no window is set.
    voting_start: datetime | None
    voting_end: datetime | None


class VotingService:
    def __init__(self, settings_gateway: AppSettingsGateway):
        self.settings_gateway = settings_gateway

    async def get_voting_window(self) -> tuple[datetime | None, datetime | None]:
        # The window without the per-user status, for callers (e.g. a guest's voting
        # page) that show when voting runs but have no ticket/status to resolve.
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
            raise AccessDenied(details={"reason": "VOTING_TICKET_REQUIRED"})
        if state.status is VotingStatus.DISABLED:
            raise AccessDenied(details={"reason": "VOTING_DISABLED"})
