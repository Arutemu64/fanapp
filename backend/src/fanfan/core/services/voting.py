from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.ticket import Ticket
from fanfan.core.models.user import User
from fanfan.core.vo.vote import VotingStatus


class VotingService:
    def __init__(self, settings_gateway: SettingsGateway):
        self.settings_gateway = settings_gateway

    async def get_voting_state(self, user: User, ticket: Ticket) -> VotingStatus:
        if user is None:
            return VotingStatus.NOT_AUTHENTICATED
        if (ticket is None) or (ticket.used_by_user_id != user.id):
            return VotingStatus.NO_TICKET
        settings = await self.settings_gateway.get_settings()
        if not settings.voting_enabled:
            return VotingStatus.DISABLED
        return VotingStatus.OPEN

    async def ensure_user_can_vote(self, user: User, ticket: Ticket | None) -> None:
        voting_state = await self.get_voting_state(user, ticket)
        if voting_state is VotingStatus.NO_TICKET:
            reason = "Для голосования необходимо привязать билет"
            raise AccessDenied(reason)
        if voting_state is VotingStatus.DISABLED:
            reason = "Голосование сейчас отключено"
            raise AccessDenied(reason)
