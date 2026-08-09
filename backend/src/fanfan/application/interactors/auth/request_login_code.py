from pydantic import BaseModel, EmailStr

from fanfan.application.interactors.auth.send_login_code_email import (
    SendLoginCodeEmail,
    SendLoginCodeEmailInput,
)
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.user import UserService
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast, RateLimitCooldown
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.services.email_login import EMAIL_CODE_REQUEST_COOLDOWN_SECONDS
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import UserRole, generate_user_id


class RequestLoginCodeInput(BaseModel):
    email: EmailStr
    # Captcha token solved by the user. Optional so the same endpoint works
    # when captcha is disabled (no token sent, no verification performed).
    captcha_token: str | None = None


class RequestLoginCode:
    def __init__(
        self,
        user_gateway: UserGateway,
        send_login_code_email: SendLoginCodeEmail,
        uow: UnitOfWork,
        user_service: UserService,
        rate_lock_factory: RateLockFactory,
        captcha_verifier: CaptchaVerifier,
    ):
        self.user_gateway = user_gateway
        self.send_login_code_email = send_login_code_email
        self.uow = uow
        self.user_service = user_service
        self.rate_lock_factory = rate_lock_factory
        self.captcha_verifier = captcha_verifier

    async def __call__(self, data: RequestLoginCodeInput) -> None:
        # Reject bots before touching the database or rate-limit budget.
        await self.captcha_verifier.verify(data.captcha_token)

        email = Email(data.email)

        lock = self.rate_lock_factory(
            f"email_code_request:{email.value}",
            cooldown_period=EMAIL_CODE_REQUEST_COOLDOWN_SECONDS,
        )
        try:
            async with lock:
                user = await self.user_gateway.get_by_email(email.value)

                # New emails are provisioned immediately so the same flow can both
                # register the account and send the one-time sign-in code.
                if user is None:
                    for _ in range(3):
                        try:
                            user = User.create(
                                id=generate_user_id(),
                                username=await self.user_service.generate_username(),
                                email=email,
                                hashed_password=None,
                                role=UserRole.VISITOR,
                            )
                            await self.user_gateway.add(user)
                            await self.uow.commit()
                        except UserAlreadyExists:
                            await self.uow.rollback()
                            user = await self.user_gateway.get_by_email(email.value)
                            if user is not None:
                                break
                        else:
                            break

                    if user is None:
                        msg = "Could not provision user for login code"
                        raise RuntimeError(msg)

                # Send the code synchronously inside the lock so a delivery
                # failure surfaces to the caller as an error instead of leaving
                # the user staring at a code that never arrives. The lock only
                # records its cooldown on a clean exit, so a failed send does not
                # burn the cooldown — the user can retry immediately.
                await self.send_login_code_email(
                    SendLoginCodeEmailInput(user_id=user.id)
                )
        except RateLimitCooldown as e:
            raise EmailCodeRequestTooFast(retry_after=e.details["retry_after"]) from e
