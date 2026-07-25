from pydantic import BaseModel

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.auth import IncorrectPassword
from fanfan.core.vo.fields import PASSWORD_FIELD


class ChangePasswordInput(BaseModel):
    old_password: str | None  # User might not have password set
    new_password: str = PASSWORD_FIELD


class ChangePassword:
    def __init__(
        self,
        password_hasher: PasswordHasher,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        session_store: SessionStore,
        uow: UnitOfWork,
    ):
        self.password_hasher = password_hasher
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.session_store = session_store
        self.uow = uow

    async def __call__(
        self,
        data: ChangePasswordInput,
    ) -> str:
        current_user = await self.current_user_provider.require_user()
        if current_user.hashed_password:
            if data.old_password:
                if not self.password_hasher.verify(
                    data.old_password, current_user.hashed_password
                ):
                    raise IncorrectPassword
            else:
                raise IncorrectPassword
        current_user.set_password_hash(self.password_hasher.hash(data.new_password))
        await self.user_gateway.save(current_user)
        await self.uow.commit()

        await self.session_store.revoke_user_sessions(current_user.id)
        return await self.session_store.create_session(current_user.id)
