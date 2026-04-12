from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.user import User


async def get_current_user(id_provider: IdProvider, user_repo: UserRepository) -> User:
    current_user_id = await id_provider.get_current_user_id()
    if current_user_id is None:
        raise UserNotAuthenticated
    current_user = await user_repo.get_by_id(current_user_id)
    if current_user is None:
        raise UserNotFound
    return current_user
