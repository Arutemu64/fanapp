import logging
from dataclasses import replace

from pydantic import MISSING, BaseModel

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider

logger = logging.getLogger(__name__)


class UpdateUserSettingsInput(BaseModel):
    # MISSING rather than None, like UpdateAppSettingsInput: a switch is on or
    # off, so an explicit null is a 422 rather than a silent no-op.
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
        # model_dump leaves out the MISSING fields, so the merge keeps their
        # current values.
        data_to_update = data.model_dump()
        current_user = await self.current_user_provider.require_user()
        current_user.set_settings(replace(current_user.settings, **data_to_update))
        if data_to_update:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
