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
from fanfan.core.services.user import UserService
from fanfan.core.utils.email import normalize_email
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
            normalized_email = normalize_email(data.email)
            try:
                # Reserve the address before insert so pending replacements on
                # other accounts are treated as conflicts too.
                existing_user = await self.user_gateway.get_user_by_any_email(
                    normalized_email
                )
                if existing_user is not None:
                    raise UserAlreadyExists

                username = await self.user_service.generate_username()
                new_user = User(
                    username=username,
                    email=normalized_email,
                    hashed_password=self.security.hash_password(data.password),
                    role=UserRole.VISITOR,
                    pending_email=None,
                    email_verified_at=None,
                )
                await self.user_gateway.add_user(new_user)
                await self.uow.commit()
            except IntegrityError as e:
                if get_constraint_name(e) in {
                    "ix_users_email",
                    "ix_users_username",
                    "ix_users_pending_email",
                }:
                    raise UserAlreadyExists from e
                raise
            else:
                await self.event_broker.publish(CreatedUserEvent(user_id=new_user.id))
