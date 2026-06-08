from pydantic import BaseModel, EmailStr

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.user import UserService
from fanfan.core.events.users import EmailLoginCodeRequested
from fanfan.core.exceptions.rate_limit import EmailCodeRequestTooFast, RateLimitCooldown
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.services.email_login import EMAIL_CODE_REQUEST_COOLDOWN_SECONDS
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserRole, generate_user_id


class RequestLoginCodeInput(BaseModel):
    email: EmailStr


class RequestLoginCode:
    def __init__(
        self,
        user_repo: UserRepository,
        event_broker: EventBroker,
        uow: UnitOfWork,
        user_service: UserService,
        rate_lock_factory: RateLockFactory,
    ):
        self.user_repo = user_repo
        self.event_broker = event_broker
        self.uow = uow
        self.user_service = user_service
        self.rate_lock_factory = rate_lock_factory

    async def __call__(self, data: RequestLoginCodeInput) -> None:
        normalized_email = normalize_email(data.email)

        lock = self.rate_lock_factory(
            f"email_code_request:{normalized_email}",
            cooldown_period=EMAIL_CODE_REQUEST_COOLDOWN_SECONDS,
        )
        try:
            async with lock:
                user = await self.user_repo.get_by_email(normalized_email)

                # Do not provision a second account if the address is
                # already reserved as another user's pending
                # replacement email.
                reserved_user = await self.user_repo.get_by_any_email(normalized_email)
                if user is None and reserved_user is not None:
                    return

                # New emails are provisioned immediately so the same flow can both
                # register the account and send the one-time sign-in code.
                if user is None:
                    for _ in range(3):
                        try:
                            user = User.create(
                                id=generate_user_id(),
                                username=await self.user_service.generate_username(),
                                email=normalized_email,
                                hashed_password=None,
                                role=UserRole.VISITOR,
                            )
                            await self.user_repo.add(user)
                            await self.uow.commit()
                        except UserAlreadyExists:
                            await self.uow.rollback()
                            user = await self.user_repo.get_by_email(normalized_email)
                            if user is not None:
                                break
                        else:
                            break

                    if user is None:
                        msg = "Could not provision user for login code"
                        raise RuntimeError(msg)

                # "Send a login code" is a command to the email subsystem,
                # not an aggregate state change, so it is published directly
                # as a service event.
                await self.event_broker.publish(
                    EmailLoginCodeRequested(user_id=user.id)
                )
        except RateLimitCooldown as e:
            raise EmailCodeRequestTooFast(retry_after=e.details["retry_after"]) from e
