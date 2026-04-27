from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.vo.user import UserRole


class GetSettings:
    def __init__(
        self,
        app_settings_repo: AppSettingsRepository,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.app_settings_repo = app_settings_repo
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider

    async def __call__(self) -> AppSettingsDTO:
        current_user = await self.current_user_provider.require_user()

        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        return AppSettingsDTO.model_validate(await self.app_settings_repo.get())
