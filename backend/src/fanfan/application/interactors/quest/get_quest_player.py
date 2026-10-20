from fanfan.application.dto.quest import QuestPlayerDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserNumber


class GetQuestPlayer:
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

    async def __call__(self, number: UserNumber) -> QuestPlayerDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.QUEST_AWARD
        )
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        player = await self.quest_award_gateway.read_player(number)
        if player is None:
            raise UserNotFound
        return player
