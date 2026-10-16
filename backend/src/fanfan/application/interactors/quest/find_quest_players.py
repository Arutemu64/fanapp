from pydantic import BaseModel, Field

from fanfan.application.dto.quest import QuestPlayerDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission

_MAX_RESULTS = 10


class FindQuestPlayersInput(BaseModel):
    search: str = Field(min_length=1, max_length=64)


class FindQuestPlayersOutput(BaseModel):
    players: list[QuestPlayerDTO]


class FindQuestPlayers:
    """Volunteers look a player up by username when their QR will not scan.

    Gated on quest:award rather than users:read: it reveals only names and
    points, never the email or ticket the user directory shows.
    """

    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: FindQuestPlayersInput) -> FindQuestPlayersOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.QUEST_AWARD
        )
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        players = await self.quest_award_gateway.read_players_by_username(
            data.search, _MAX_RESULTS
        )
        return FindQuestPlayersOutput(players=players)
