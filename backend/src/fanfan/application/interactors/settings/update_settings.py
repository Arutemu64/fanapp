import logging

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class UpdateAppSettingsInput(BaseModel):
    voting_enabled: bool | None = None
    announcement_timeout: int | None = Field(default=None, ge=1)


class UpdateSettings:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: UpdateAppSettingsInput) -> None:
        # Only persist fields that were actually sent by the client.
        data_to_update = data.model_dump(exclude_unset=True)
        current_user = await self.current_user_provider.require_user()
        if current_user.role is not UserRole.ORG:
            raise AccessDenied
        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        update_flag = False

        if (voting_enabled := data_to_update.get("voting_enabled")) is not None:
            settings.set_voting_enabled(voting_enabled)
            update_flag = True

        if (
            announcement_timeout := data_to_update.get("announcement_timeout")
        ) is not None:
            settings.limits.set_announcement_timeout(announcement_timeout)
            update_flag = True

        if not update_flag:
            return

        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Festival settings updated by user %s",
            current_user.id,
            extra={"settings": settings},
        )
