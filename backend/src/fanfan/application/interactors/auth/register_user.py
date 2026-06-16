from pydantic import BaseModel, EmailStr

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.user import UserService
from fanfan.core.exceptions.users import UserAlreadyExists
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.fields import PASSWORD_FIELD
from fanfan.core.vo.user import UserRole, generate_user_id


class RegisterUserInput(BaseModel):
    email: EmailStr
    password: str = PASSWORD_FIELD


class RegisterUser:
    def __init__(
        self,
        password_hasher: PasswordHasher,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        user_service: UserService,
    ):
        self.password_hasher = password_hasher
        self.user_gateway = user_gateway
        self.uow = uow
        self.user_service = user_service

    async def __call__(self, data: RegisterUserInput) -> None:
        email = Email(data.email)
        # If the address is already used (or reserved as another account's
        # pending replacement), silently no-op: never reveal that it is taken
        # (prevents account enumeration) and never touch the existing account
        # (overwriting its password would be account takeover). The caller
        # always sees the same neutral success.
        existing_user = await self.user_gateway.get_by_email(email.value)
        if existing_user is not None:
            return

        username = await self.user_service.generate_username()
        new_user = User.create(
            id=generate_user_id(),
            username=username,
            email=email,
            hashed_password=self.password_hasher.hash(data.password),
            role=UserRole.VISITOR,
        )
        try:
            await self.user_gateway.add(new_user)
            await self.uow.commit()
        except UserAlreadyExists:
            # Lost a race with a concurrent registration for the same email.
            # Keep the response neutral instead of leaking a 409 conflict.
            await self.uow.rollback()
