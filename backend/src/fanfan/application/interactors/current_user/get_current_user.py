from fanfan.application.dto.user import CurrentUserDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound


class GetCurrentUser:
    def __init__(self, user_repo: UserRepository, id_provider: IdProvider) -> None:
        self.user_repo = user_repo
        self.id_provider = id_provider

    async def __call__(self) -> CurrentUserDTO:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        user = await self.user_repo.read_current_user(current_user_id)
        if user is None:
            raise UserNotFound
        return user
