import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager

logger = logging.getLogger(__name__)


class UpdateUserSettingsInput(BaseModel):
    receive_all_announcements: bool | None = None
    receive_telegram_notifications: bool | None = None


class UpdateUserSettings:
    def __init__(
        self,
        user_repo: UserRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ):
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: UpdateUserSettingsInput) -> None:
        data_to_update = data.model_dump(exclude_unset=True)
        update_flag = False
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        if (
            receive_all_announcements := data_to_update.get("receive_all_announcements")
        ) is not None:
            current_user.settings.receive_all_announcements = receive_all_announcements
            update_flag = True
        if (
            receive_telegram_notifications := data_to_update.get(
                "receive_telegram_notifications"
            )
        ) is not None:
            current_user.settings.receive_telegram_notifications = (
                receive_telegram_notifications
            )
            update_flag = True
        if update_flag:
            await self.user_repo.save(current_user)
            await self.trx.commit()
