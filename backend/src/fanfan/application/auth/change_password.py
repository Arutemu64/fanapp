from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import IncorrectPassword, UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.auth import AuthService
from fanfan.core.vo.fields import PASSWORD_FIELD


class ChangePasswordCommand(BaseModel):
    old_password: str | None  # User might not have password set
    new_password: str = PASSWORD_FIELD


class ChangePassword:
    def __init__(
        self,
        auth: AuthService,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ):
        self.auth = auth
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: ChangePasswordCommand) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            if current_user.hashed_password:
                # User has password set
                if data.old_password:
                    if not self.auth.verify_password(
                        data.old_password, current_user.hashed_password
                    ):
                        raise IncorrectPassword
                else:
                    raise IncorrectPassword
            current_user.hashed_password = self.auth.hash_password(data.new_password)
            await self.user_gateway.save_user(current_user)
            await self.uow.commit()
