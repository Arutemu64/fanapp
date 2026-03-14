import logging

from pydantic import BaseModel, Field

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


class UpdateAppSettingsCommand(BaseModel):
    # Keep the payload small and explicit so the organizer page can update
    # only the settings it actually edits today.
    voting_enabled: bool | None = None
    announcement_timeout: int | None = Field(default=None, ge=1)


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

    async def __call__(self, data: UpdateAppSettingsCommand) -> None:
        # Only persist fields that were actually sent by the client.
        data_to_update = data.model_dump(exclude_unset=True)
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

        update_flag = False

        if (voting_enabled := data_to_update.get("voting_enabled")) is not None:
            settings.voting_enabled = voting_enabled
            update_flag = True

        if (
            announcement_timeout := data_to_update.get("announcement_timeout")
        ) is not None:
            settings.limits.announcement_timeout = announcement_timeout
            update_flag = True

        if not update_flag:
            return

        async with self.uow:
            await self.settings_gateway.save_settings(settings)
            await self.uow.commit()
            logger.info(
                "Festival settings updated by user %s",
                current_user.id,
                extra={"settings": settings},
            )
