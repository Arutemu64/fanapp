import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider

logger = logging.getLogger(__name__)


class UpdateUserSettingsInput(BaseModel):
    receive_all_announcements: bool | None = None
    receive_telegram_notifications: bool | None = None


class UpdateUserSettings:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: UpdateUserSettingsInput) -> None:
        data_to_update = data.model_dump(exclude_unset=True)
        update_flag = False
        current_user = await self.current_user_provider.require_user()
        if (
            receive_all_announcements := data_to_update.get("receive_all_announcements")
        ) is not None:
            current_user.settings.set_receive_all_announcements(
                receive_all_announcements
            )
            update_flag = True
        if (
            receive_telegram_notifications := data_to_update.get(
                "receive_telegram_notifications"
            )
        ) is not None:
            current_user.settings.set_receive_telegram_notifications(
                receive_telegram_notifications
            )
            update_flag = True
        if update_flag:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
