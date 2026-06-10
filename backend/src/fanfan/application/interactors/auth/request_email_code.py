from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.users import EmailConfirmationCodeRequested
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast, RateLimitCooldown
from fanfan.core.exceptions.users import UserHasNoEmail
from fanfan.core.services.email_login import EMAIL_CODE_REQUEST_COOLDOWN_SECONDS


class RequestEmailCode:
    def __init__(
        self,
        user_gateway: UserGateway,
        event_broker: EventBroker,
        current_user_provider: CurrentUserProvider,
        rate_lock_factory: RateLockFactory,
    ):
        self.user_gateway = user_gateway
        self.event_broker = event_broker
        self.current_user_provider = current_user_provider
        self.rate_lock_factory = rate_lock_factory

    async def __call__(self) -> None:
        current_user = await self.current_user_provider.require_user()

        target_email = current_user.pending_email or current_user.email
        if target_email is None:
            raise UserHasNoEmail

        email_value = target_email.value

        lock = self.rate_lock_factory(
            f"email_code_request:{email_value}",
            cooldown_period=EMAIL_CODE_REQUEST_COOLDOWN_SECONDS,
        )
        try:
            async with lock:
                # "Send a confirmation code" is a command to the email
                # subsystem, not an aggregate state change, so it is published
                # directly as a service event.
                await self.event_broker.publish(
                    EmailConfirmationCodeRequested(user_id=current_user.id)
                )
        except RateLimitCooldown as e:
            raise EmailCodeRequestTooFast(retry_after=e.details["retry_after"]) from e
