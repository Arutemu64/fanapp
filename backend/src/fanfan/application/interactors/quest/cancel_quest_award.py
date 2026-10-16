import logging
from datetime import UTC, datetime, timedelta

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.quest import QuestAwardNotFound
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.quest import QuestAwardId

logger = logging.getLogger(__name__)


class CancelQuestAward:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, award_id: QuestAwardId) -> None:
        current_user = await self.current_user_provider.require_user()
        can_manage = await self.perm_service.has(current_user, Permission.QUEST_MANAGE)
        if not can_manage:
            await self.perm_service.ensure(
                user=current_user, permission=Permission.QUEST_AWARD
            )
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        award = await self.quest_award_gateway.get_for_update(award_id)
        if award is None:
            raise QuestAwardNotFound

        award.cancel(
            by_user_id=current_user.id,
            can_manage=can_manage,
            cancel_window=timedelta(minutes=settings.quest.cancel_window_minutes),
            now=datetime.now(UTC),
        )
        await self.quest_award_gateway.save(award)
        await self.uow.commit()

        logger.info(
            "Quest award cancelled",
            extra={"award_id": str(award.id), "actor_id": str(current_user.id)},
        )
