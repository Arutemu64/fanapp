from pydantic import BaseModel, EmailStr

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.services.security import SecurityService
from fanfan.core.exceptions.auth import InvalidCredentials
from fanfan.core.utils.email import normalize_email


class AuthenticateUserInput(BaseModel):
    email: EmailStr
    password: str


class AuthenticateUser:
    def __init__(
        self,
        user_repo: UserRepository,
        security: SecurityService,
        session_store: SessionStore,
    ):
        self.user_repo = user_repo
        self.security = security
        self.session_store = session_store
        self.dummy_hash = self.security.hash_password("dummy_password")

    async def __call__(self, data: AuthenticateUserInput) -> str:
        normalized_email = normalize_email(data.email)
        user = await self.user_repo.get_by_email(normalized_email)
        if user is None:
            # Prevent timing attack
            self.security.verify_password(data.password, self.dummy_hash)
            raise InvalidCredentials
        # Social-only accounts may have no password yet.
        # Return a normal auth failure instead of crashing on password verification.
        if user.hashed_password is None:
            raise InvalidCredentials
        if not self.security.verify_password(data.password, user.hashed_password):
            raise InvalidCredentials

        return await self.session_store.create_session(user.id)
