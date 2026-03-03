from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.core.events.users import CreatedUserEvent
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.services.security import SecurityService
from fanfan.core.services.user import UserService
from fanfan.core.vo.fields import PASSWORD_FIELD
from fanfan.core.vo.user import UserRole


class RegisterUserCommand(BaseModel):
    email: EmailStr = Field(...)
    password: str = PASSWORD_FIELD


class RegisterUser:
    def __init__(
        self,
        security: SecurityService,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        event_broker: EventBroker,
        user_service: UserService,
    ):
        self.security = security
        self.user_gateway = user_gateway
        self.uow = uow
        self.event_broker = event_broker
        self.user_service = user_service

    async def __call__(self, data: RegisterUserCommand) -> None:
        async with self.uow:
            try:
                username = await self.user_service.generate_username()
                new_user = User(
                    username=username,
                    email=data.email,
                    hashed_password=self.security.hash_password(data.password),
                    role=UserRole.VISITOR,
                    is_verified=False,
                )
                await self.user_gateway.add_user(new_user)
                await self.uow.commit()
            except IntegrityError as e:
                # TODO add check
                raise UserAlreadyExists from e
            else:
                await self.event_broker.publish(CreatedUserEvent(user_id=new_user.id))
