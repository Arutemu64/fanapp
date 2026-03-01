from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.auth import AuthService


class AuthenticateUserCommand(BaseModel):
    login: str
    password: str


class AuthenticateUser:
    def __init__(self, user_gateway: UserGateway, auth: AuthService):
        self.user_gateway = user_gateway
        self.auth = auth
        self.dummy_hash = self.auth.hash_password("dummy_password")

    async def __call__(self, data: AuthenticateUserCommand) -> Token:
        user = await self.user_gateway.get_user_by_username(
            data.login
        ) or await self.user_gateway.get_user_by_email(data.login)
        if user is None:
            # Prevent timing attack
            self.auth.verify_password(data.password, self.dummy_hash)
            raise UserNotFound
        if not self.auth.verify_password(data.password, user.hashed_password):
            raise AuthenticationError

        return self.auth.create_token(user_id=user.id)
