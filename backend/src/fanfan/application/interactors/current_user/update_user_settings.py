import logging

from pydantic import MISSING

from fanfan.application.dto.input import InputModel
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider

logger = logging.getLogger(__name__)


class UpdateUserSettingsInput(InputModel):
    receive_all_announcements: bool | MISSING = MISSING
    receive_telegram_notifications: bool | MISSING = MISSING
    receive_vk_notifications: bool | MISSING = MISSING


class UpdateUserSettings:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: UpdateUserSettingsInput) -> None:
        data_to_update = data.model_dump()
        current_user = await self.current_user_provider.require_user()
        current_user.update_settings(
            receive_all_announcements=data_to_update.get("receive_all_announcements"),
            receive_telegram_notifications=data_to_update.get(
                "receive_telegram_notifications"
            ),
            receive_vk_notifications=data_to_update.get("receive_vk_notifications"),
        )
        if data_to_update:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
