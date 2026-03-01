import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound

logger = logging.getLogger(__name__)


class UpdateUserSettingsCommand(BaseModel):
    receive_all_announcements: bool | None = None


class UpdateUserSettings:
    def __init__(
        self, user_gateway: UserGateway, id_provider: IdProvider, uow: UnitOfWork
    ):
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: UpdateUserSettingsCommand) -> None:
        data_to_update = data.model_dump(exclude_unset=True)
        async with self.uow:
            update_flag = False
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            if receive_all_announcements := data_to_update.get(
                "receive_all_announcements"
            ):
                current_user.settings.receive_all_announcements = (
                    receive_all_announcements
                )
                update_flag = True
            if update_flag:
                await self.user_gateway.save_user(current_user)
                await self.uow.commit()
        return
