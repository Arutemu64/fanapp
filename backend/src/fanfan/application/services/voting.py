from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.vote import VotingStatus


class VotingService:
    def __init__(self, settings_repo: AppSettingsRepository):
        self.settings_repo = settings_repo

    async def get_voting_state(self, user: User, ticket: Ticket | None) -> VotingStatus:
        if (ticket is None) or (ticket.used_by_user_id != user.id):
            return VotingStatus.NO_TICKET
        settings = await self.settings_repo.get()
        if not settings.voting_enabled:
            return VotingStatus.DISABLED
        return VotingStatus.OPEN

    async def ensure_user_can_vote(self, user: User, ticket: Ticket | None) -> None:
        voting_state = await self.get_voting_state(user, ticket)
        if voting_state is VotingStatus.NO_TICKET:
            raise AccessDenied(details={"reason": "VOTING_TICKET_REQUIRED"})
        if voting_state is VotingStatus.DISABLED:
            raise AccessDenied(details={"reason": "VOTING_DISABLED"})
