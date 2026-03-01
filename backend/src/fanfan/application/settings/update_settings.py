import logging

from adaptix import Retort, name_mapping

from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import SettingsNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class UpdateSettings:
    def __init__(
        self,
        settings_gateway: SettingsGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow
        self.retort = Retort(recipe=[name_mapping(omit_default=True)])

    async def set_voting(self, voting_enabled: bool) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        if current_user.role is not UserRole.ORG:
            raise AccessDenied
        settings = await self.settings_gateway.get_settings()
        if settings is None:
            raise SettingsNotFound
        settings.voting_enabled = voting_enabled
        async with self.uow:
            await self.settings_gateway.save_settings(settings)
            await self.uow.commit()
            logger.info(
                "Voting toggled by user %s",
                current_user.id,
                extra={"settings": settings},
            )
