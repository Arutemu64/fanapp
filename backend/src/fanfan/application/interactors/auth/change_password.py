from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.security import SecurityService
from fanfan.core.exceptions.auth import IncorrectPassword
from fanfan.core.vo.fields import PASSWORD_FIELD


class ChangePasswordInput(BaseModel):
    old_password: str | None  # User might not have password set
    new_password: str = PASSWORD_FIELD


class ChangePassword:
    def __init__(
        self,
        security: SecurityService,
        user_repo: UserRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ):
        self.security = security
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: ChangePasswordInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider, user_repo=self.user_repo
        )
        if current_user.hashed_password:
            # User has password set
            if data.old_password:
                if not self.security.verify_password(
                    data.old_password, current_user.hashed_password
                ):
                    raise IncorrectPassword
            else:
                raise IncorrectPassword
        current_user.hashed_password = self.security.hash_password(data.new_password)
        await self.user_repo.save(current_user)
        await self.trx.commit()
