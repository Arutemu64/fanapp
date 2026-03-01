from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.users import EmailVerificationRequestedEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import EmailAlreadyExists, UserNotFound


class ChangeEmailCommand(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        event_broker: EventBroker,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ):
        self.event_broker = event_broker
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: ChangeEmailCommand) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            try:
                current_user.email = data.new_email
                current_user.is_verified = False
                await self.user_gateway.save_user(current_user)
                await self.uow.commit()
            except IntegrityError as e:
                raise EmailAlreadyExists from e
            await self.event_broker.publish(
                EmailVerificationRequestedEvent(user_id=current_user.id)
            )
