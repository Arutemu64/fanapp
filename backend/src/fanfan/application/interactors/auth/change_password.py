from pydantic import BaseModel

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
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
        current_user_provider: CurrentUserProvider,
        session_store: SessionStore,
        uow: UnitOfWork,
    ):
        self.security = security
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.session_store = session_store
        self.uow = uow

    async def __call__(
        self,
        data: ChangePasswordInput,
    ) -> str:
        current_user = await self.current_user_provider.require_user()
        if current_user.hashed_password:
            # User has password set
            if data.old_password:
                if not self.security.verify_password(
                    data.old_password, current_user.hashed_password
                ):
                    raise IncorrectPassword
            else:
                raise IncorrectPassword
        current_user.set_password_hash(self.security.hash_password(data.new_password))
        await self.user_repo.save(current_user)
        await self.uow.commit()

        # Security-first behavior: revoke every active session after password change.
        await self.session_store.revoke_user_sessions(current_user.id)
        return await self.session_store.create_session(current_user.id)
