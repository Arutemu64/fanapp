from pydantic import BaseModel, EmailStr

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.security import SecurityService
from fanfan.application.services.user import UserService
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.fields import PASSWORD_FIELD
from fanfan.core.vo.user import UserRole, generate_user_id


class RegisterUserInput(BaseModel):
    email: EmailStr
    password: str = PASSWORD_FIELD


class RegisterUser:
    def __init__(
        self,
        security: SecurityService,
        user_repo: UserRepository,
        trx: TransactionManager,
        event_broker: EventBroker,
        user_service: UserService,
    ):
        self.security = security
        self.user_repo = user_repo
        self.trx = trx
        self.event_broker = event_broker
        self.user_service = user_service

    async def __call__(self, data: RegisterUserInput) -> None:
        normalized_email = normalize_email(data.email)
        # Reserve the address before insert so pending replacements on
        # other accounts are treated as conflicts too.
        existing_user = await self.user_repo.get_by_any_email(normalized_email)
        if existing_user is not None:
            raise UserAlreadyExists

        username = await self.user_service.generate_username()
        new_user = User.create(
            id=generate_user_id(),
            username=username,
            email=normalized_email,
            hashed_password=self.security.hash_password(data.password),
            role=UserRole.VISITOR,
        )
        await self.user_repo.add(new_user)
        await self.trx.commit()
        for event in new_user.pull_events():
            await self.event_broker.publish(event)
