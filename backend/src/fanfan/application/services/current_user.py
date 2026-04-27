from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserId


class CurrentUserProvider:
    def __init__(self, id_provider: IdProvider, user_repo: UserRepository) -> None:
        self.id_provider = id_provider
        self.user_repo = user_repo

    async def get_user_id(self) -> UserId | None:
        return await self.id_provider.get_current_user_id()

    async def require_user_id(self) -> UserId:
        current_user_id = await self.get_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        return current_user_id

    async def get_user(self) -> User | None:
        current_user_id = await self.get_user_id()
        if current_user_id is None:
            return None

        return await self.user_repo.get_by_id(current_user_id)

    async def require_user(self) -> User:
        current_user_id = await self.require_user_id()
        current_user = await self.user_repo.get_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        return current_user
