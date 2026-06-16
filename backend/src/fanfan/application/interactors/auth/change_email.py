from pydantic import BaseModel, EmailStr

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.users import EmailConfirmationCodeRequested
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast, RateLimitCooldown
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.services.email_login import EMAIL_CODE_REQUEST_COOLDOWN_SECONDS
from fanfan.core.vo.email import Email


class ChangeEmailInput(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        event_broker: EventBroker,
        rate_lock_factory: RateLockFactory,
    ):
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.event_broker = event_broker
        self.rate_lock_factory = rate_lock_factory

    async def __call__(self, data: ChangeEmailInput) -> None:
        new_email = Email(data.new_email)
        current_user = await self.current_user_provider.require_user()

        if current_user.email == new_email:
            return

        existing_user = await self.user_gateway.get_by_email(new_email.value)
        if existing_user is not None and existing_user.id != current_user.id:
            raise EmailAlreadyExists

        lock = self.rate_lock_factory(
            f"email_code_request:{new_email.value}",
            cooldown_period=EMAIL_CODE_REQUEST_COOLDOWN_SECONDS,
        )
        try:
            async with lock:
                await self.event_broker.publish(
                    EmailConfirmationCodeRequested(
                        user_id=current_user.id,
                        target_email=new_email.value,
                    )
                )
        except RateLimitCooldown as e:
            raise EmailCodeRequestTooFast(retry_after=e.details["retry_after"]) from e
