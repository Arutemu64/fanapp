from fanfan.application.dto.user import UsernameSuggestionDTO
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.user import UserService


class SuggestUsername:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        user_service: UserService,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.user_service = user_service

    async def __call__(self) -> UsernameSuggestionDTO:
        await self.current_user_provider.require_user_id()
        username = await self.user_service.generate_username()
        return UsernameSuggestionDTO(username=username)
