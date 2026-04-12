import logging

from pydantic import BaseModel, Field

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.settings import AppAppSettingsNotFound
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class UpdateAppSettingsInput(BaseModel):
    voting_enabled: bool | None = None
    announcement_timeout: int | None = Field(default=None, ge=1)


class UpdateSettings:
    def __init__(
        self,
        settings_repo: AppSettingsRepository,
        user_repo: UserRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ) -> None:
        self.settings_repo = settings_repo
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: UpdateAppSettingsInput) -> None:
        # Only persist fields that were actually sent by the client.
        data_to_update = data.model_dump(exclude_unset=True)
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        if current_user.role is not UserRole.ORG:
            raise AccessDenied
        settings = await self.settings_repo.get()
        if settings is None:
            raise AppAppSettingsNotFound

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

        await self.settings_repo.save(settings)
        await self.trx.commit()
        logger.info(
            "Festival settings updated by user %s",
            current_user.id,
            extra={"settings": settings},
        )
