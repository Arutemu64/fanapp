from itsdangerous import BadSignature, SignatureExpired
from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.exceptions.auth import InvalidToken, TokenExpired
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.auth import EMAIL_VERIFY_SALT, AuthService


class VerifyEmailCommand(BaseModel):
    token: str


class VerifyEmail:
    def __init__(self, user_gateway: UserGateway, auth: AuthService, uow: UnitOfWork):
        self.user_gateway = user_gateway
        self.auth = auth
        self.uow = uow

    async def __call__(self, data: VerifyEmailCommand) -> None:
        async with self.uow:
            try:
                user_id = self.auth.verify_signature(
                    data.token, salt=EMAIL_VERIFY_SALT, max_age=3600
                )
            except SignatureExpired as e:
                raise TokenExpired from e
            except BadSignature as e:
                raise InvalidToken from e

            user = await self.user_gateway.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound
            user.is_verified = True
            await self.user_gateway.save_user(user)
            await self.uow.commit()
