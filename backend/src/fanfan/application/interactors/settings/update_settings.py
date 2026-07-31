import logging

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class UpdateAppSettingsInput(BaseModel):
    voting_enabled: bool | None = None
    announcement_timeout_seconds: int | None = Field(default=None, ge=1)
    transition_buffer_seconds: int | None = Field(default=None, ge=0)


class UpdateSettings:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: UpdateAppSettingsInput) -> None:
        data_to_update = data.model_dump(exclude_unset=True)
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SETTINGS_MANAGE
        )
        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        update_flag = False

        if (voting_enabled := data_to_update.get("voting_enabled")) is not None:
            settings.set_voting_enabled(enabled=voting_enabled)
            update_flag = True

        if (
            announcement_timeout_seconds := data_to_update.get(
                "announcement_timeout_seconds"
            )
        ) is not None:
            settings.update_limits(
                announcement_timeout_seconds=announcement_timeout_seconds
            )
            update_flag = True

        if (
            transition_buffer_seconds := data_to_update.get("transition_buffer_seconds")
        ) is not None:
            settings.update_limits(transition_buffer_seconds=transition_buffer_seconds)
            update_flag = True

        if not update_flag:
            return

        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Festival settings updated",
            extra={"actor_id": str(current_user.id)},
        )
