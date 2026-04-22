from pydantic import BaseModel, EmailStr, Field

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.user import UserService
from fanfan.core.events.users import CreatedUserEvent, EmailLoginCodeRequestedEvent
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserRole


class RequestLoginCodeInput(BaseModel):
    email: EmailStr = Field(...)


class RequestLoginCode:
    def __init__(
        self,
        user_repo: UserRepository,
        event_broker: EventBroker,
        trx: TransactionManager,
        user_service: UserService,
    ):
        self.user_repo = user_repo
        self.event_broker = event_broker
        self.trx = trx
        self.user_service = user_service

    async def __call__(self, data: RequestLoginCodeInput) -> None:
        normalized_email = normalize_email(data.email)
        user = await self.user_repo.get_by_email(normalized_email)

        # Do not provision a second account if the address is already reserved as
        # another user's pending replacement email.
        reserved_user = await self.user_repo.get_by_any_email(normalized_email)
        if user is None and reserved_user is not None:
            return

        # New emails are provisioned immediately so the same flow can both
        # register the account and send the one-time sign-in code.
        if user is None:
            for _ in range(3):
                try:
                    user = User(
                        username=await self.user_service.generate_username(),
                        email=normalized_email,
                        hashed_password=None,
                        role=UserRole.VISITOR,
                        pending_email=None,
                        email_verified_at=None,
                    )
                    await self.user_repo.add(user)
                    await self.trx.commit()
                except UserAlreadyExists:
                    await self.trx.rollback()
                    user = await self.user_repo.get_by_email(normalized_email)
                    if user is not None:
                        break
                else:
                    await self.event_broker.publish(CreatedUserEvent(user_id=user.id))
                    break

            if user is None:
                msg = "Could not provision user for login code"
                raise RuntimeError(msg)

        await self.event_broker.publish(EmailLoginCodeRequestedEvent(user_id=user.id))
