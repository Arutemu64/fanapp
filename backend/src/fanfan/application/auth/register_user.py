from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.constraints import get_constraint_name
from fanfan.core.events.users import CreatedUserEvent
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.services.security import SecurityService
from fanfan.core.vo.fields import PASSWORD_FIELD, USERNAME_FIELD
from fanfan.core.vo.user import Username, UserRole


class RegisterUserCommand(BaseModel):
    email: EmailStr = Field(...)
    username: str = USERNAME_FIELD
    password: str = PASSWORD_FIELD


class RegisterUser:
    def __init__(
        self,
        security: SecurityService,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        event_broker: EventBroker,
    ):
        self.security = security
        self.user_gateway = user_gateway
        self.uow = uow
        self.event_broker = event_broker

    async def __call__(self, data: RegisterUserCommand) -> None:
        async with self.uow:
            try:
                new_user = User(
                    username=Username(data.username),
                    email=data.email,
                    hashed_password=self.security.hash_password(data.password),
                    role=UserRole.VISITOR,
                    is_verified=False,
                )
                await self.user_gateway.add_user(new_user)
                await self.uow.commit()
            except IntegrityError as e:
                if get_constraint_name(e) in {"uq_users_email", "uq_users_username"}:
                    raise UserAlreadyExists from e
                raise
            else:
                await self.event_broker.publish(CreatedUserEvent(user_id=new_user.id))
