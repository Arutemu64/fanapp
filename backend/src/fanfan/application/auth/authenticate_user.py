from pydantic import BaseModel, EmailStr

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.security import SecurityService
from fanfan.core.utils.email import normalize_email


class AuthenticateUserCommand(BaseModel):
    email: EmailStr
    password: str


class AuthenticateUser:
    def __init__(self, user_gateway: UserGateway, security: SecurityService):
        self.user_gateway = user_gateway
        self.security = security
        self.dummy_hash = self.security.hash_password("dummy_password")

    async def __call__(self, data: AuthenticateUserCommand) -> Token:
        normalized_email = normalize_email(data.email)
        user = await self.user_gateway.get_user_by_email(normalized_email)
        if user is None:
            # Prevent timing attack
            self.security.verify_password(data.password, self.dummy_hash)
            raise UserNotFound
        # Social-only accounts may have no password yet.
        # Return a normal auth failure instead of crashing on password verification.
        if user.hashed_password is None:
            raise AuthenticationError
        if not self.security.verify_password(data.password, user.hashed_password):
            raise AuthenticationError

        return self.security.create_token(user_id=user.id)
