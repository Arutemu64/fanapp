from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.vo.user import UserRole


class GetSettings:
    def __init__(
        self,
        app_settings_repo: AppSettingsRepository,
        user_repo: UserRepository,
        id_provider: IdProvider,
    ) -> None:
        self.app_settings_repo = app_settings_repo
        self.user_repo = user_repo
        self.id_provider = id_provider

    async def __call__(self) -> AppSettingsDTO:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )

        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        return AppSettingsDTO.model_validate(await self.app_settings_repo.get())
