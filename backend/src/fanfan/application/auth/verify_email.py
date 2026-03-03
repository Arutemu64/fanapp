from itsdangerous import BadSignature, SignatureExpired
from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.auth_token_registry import AuthTokenRegistry
from fanfan.core.exceptions.auth import InvalidToken, TokenExpired
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.email_verification import (
    EMAIL_VERIFY_MAX_AGE_SECONDS,
    EmailVerificationService,
)


class VerifyEmailCommand(BaseModel):
    token: str


class VerifyEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        email_verification: EmailVerificationService,
        token_registry: AuthTokenRegistry,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.email_verification = email_verification
        self.token_registry = token_registry
        self.uow = uow

    async def __call__(self, data: VerifyEmailCommand) -> None:
        async with self.uow:
            try:
                token_data = self.email_verification.verify_token(data.token)
            except SignatureExpired as e:
                raise TokenExpired from e
            except BadSignature as e:
                raise InvalidToken from e

            is_fresh = await self.token_registry.consume_email_verification_nonce(
                nonce=token_data.nonce,
                ttl_seconds=EMAIL_VERIFY_MAX_AGE_SECONDS,
            )
            if not is_fresh:
                raise InvalidToken

            user = await self.user_gateway.get_user_by_id(token_data.user_id)
            if user is None:
                raise UserNotFound

            user.is_verified = True
            await self.user_gateway.save_user(user)
            await self.uow.commit()
