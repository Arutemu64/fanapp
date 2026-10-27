import logging

from pydantic import BaseModel, EmailStr

from fanfan.application.interactors.auth.send_login_code_email import (
    SendLoginCodeEmail,
    SendLoginCodeEmailInput,
)
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.user import UserService
from fanfan.core.exceptions.rate_limit import (
    CooldownActive,
    EmailCodeRequestTooFast,
    TooManyAttempts,
    TooManyLoginCodeRequests,
)
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.services.email_login import EMAIL_CODE_REQUEST_COOLDOWN_SECONDS
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import UserRole, generate_user_id

logger = logging.getLogger(__name__)

LOGIN_CODE_IP_MAX_REQUESTS = 20
LOGIN_CODE_IP_WINDOW_SECONDS = 600


class RequestLoginCodeInput(BaseModel):
    email: EmailStr
    captcha_token: str | None = None
    client_ip: str | None = None


class RequestLoginCode:
    def __init__(
        self,
        user_gateway: UserGateway,
        send_login_code_email: SendLoginCodeEmail,
        uow: UnitOfWork,
        user_service: UserService,
        cooldown: Cooldown,
        rate_limiter: RateLimiter,
        captcha_verifier: CaptchaVerifier,
    ) -> None:
        self.user_gateway = user_gateway
        self.send_login_code_email = send_login_code_email
        self.uow = uow
        self.user_service = user_service
        self.cooldown = cooldown
        self.rate_limiter = rate_limiter
        self.captcha_verifier = captcha_verifier

    async def __call__(self, data: RequestLoginCodeInput) -> None:
        if data.client_ip:
            await self._register_ip_attempt(data.client_ip)

        await self.captcha_verifier.verify(data.captcha_token)

        email = Email(data.email)

        claim = self.cooldown.claim(
            f"email_code_request:{email.value}", EMAIL_CODE_REQUEST_COOLDOWN_SECONDS
        )
        try:
            async with claim:
                user = await self._get_or_create_user(email)
                await self.send_login_code_email(
                    SendLoginCodeEmailInput(user_id=user.id)
                )
        except CooldownActive as e:
            raise EmailCodeRequestTooFast(retry_after=e.details["retry_after"]) from e

    async def _get_or_create_user(self, email: Email) -> User:
        user = await self.user_gateway.get_by_email(email.value)
        if user is not None:
            return user
        for _ in range(3):
            user = await self._try_create_user(email)
            if user is not None:
                return user
        msg = "Could not provision user for login code"
        raise RuntimeError(msg)

    async def _try_create_user(self, email: Email) -> User | None:
        user = User.create(
            id=generate_user_id(),
            username=await self.user_service.generate_username(),
            email=email,
            hashed_password=None,
            role=UserRole.VISITOR,
        )
        try:
            await self.user_gateway.add(user)
            await self.uow.commit()
        except UserAlreadyExists:
            await self.uow.rollback()
            return await self.user_gateway.get_by_email(email.value)
        return user

    async def _register_ip_attempt(self, client_ip: str) -> None:
        try:
            await self.rate_limiter.hit(
                f"login_code:ip:{client_ip}",
                limit=LOGIN_CODE_IP_MAX_REQUESTS,
                window_seconds=LOGIN_CODE_IP_WINDOW_SECONDS,
            )
        except TooManyAttempts as e:
            logger.warning(
                "Login code request blocked: too many requests",
                extra={"client_ip": client_ip},
            )
            raise TooManyLoginCodeRequests(retry_after=e.details["retry_after"]) from e
