from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.constraints import get_constraint_name
from fanfan.core.events.users import CreatedUserEvent, EmailMagicLinkRequestedEvent
from fanfan.core.models.user import User
from fanfan.core.services.user import UserService
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserRole


class RequestMagicLinkCommand(BaseModel):
    email: EmailStr = Field(...)


class RequestMagicLink:
    def __init__(
        self,
        user_gateway: UserGateway,
        event_broker: EventBroker,
        uow: UnitOfWork,
        user_service: UserService,
    ):
        self.user_gateway = user_gateway
        self.event_broker = event_broker
        self.uow = uow
        self.user_service = user_service

    async def __call__(self, data: RequestMagicLinkCommand) -> None:
        normalized_email = normalize_email(data.email)
        user = await self.user_gateway.get_user_by_email(normalized_email)

        # Do not provision a second account if the address is already reserved as
        # another user's pending replacement email.
        reserved_user = await self.user_gateway.get_user_by_any_email(normalized_email)
        if user is None and reserved_user is not None:
            return

        # New emails are provisioned immediately so the same flow can both
        # register the account and send the one-time sign-in link.
        if user is None:
            async with self.uow:
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
                        await self.user_gateway.add_user(user)
                        await self.uow.commit()
                    except IntegrityError as e:
                        await self.uow.rollback()
                        constraint_name = get_constraint_name(e)
                        if constraint_name in {
                            "ix_users_email",
                            "ix_users_pending_email",
                        }:
                            user = await self.user_gateway.get_user_by_email(
                                normalized_email
                            )
                            if user is not None:
                                break
                            continue
                        if constraint_name == "ix_users_username":
                            continue
                        raise
                    else:
                        await self.event_broker.publish(
                            CreatedUserEvent(user_id=user.id)
                        )
                        break

            if user is None:
                msg = "Could not provision user for magic link"
                raise RuntimeError(msg)

        await self.event_broker.publish(EmailMagicLinkRequestedEvent(user_id=user.id))
