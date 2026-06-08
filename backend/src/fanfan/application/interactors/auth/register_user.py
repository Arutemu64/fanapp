from pydantic import BaseModel, EmailStr

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
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
        uow: UnitOfWork,
        user_service: UserService,
    ):
        self.security = security
        self.user_repo = user_repo
        self.uow = uow
        self.user_service = user_service

    async def __call__(self, data: RegisterUserInput) -> None:
        normalized_email = normalize_email(data.email)
        # If the address is already used (or reserved as another account's
        # pending replacement), silently no-op: never reveal that it is taken
        # (prevents account enumeration) and never touch the existing account
        # (overwriting its password would be account takeover). The caller
        # always sees the same neutral success.
        existing_user = await self.user_repo.get_by_any_email(normalized_email)
        if existing_user is not None:
            return

        username = await self.user_service.generate_username()
        new_user = User.create(
            id=generate_user_id(),
            username=username,
            email=normalized_email,
            hashed_password=self.security.hash_password(data.password),
            role=UserRole.VISITOR,
        )
        try:
            await self.user_repo.add(new_user)
            await self.uow.commit()
        except UserAlreadyExists:
            # Lost a race with a concurrent registration for the same email.
            # Keep the response neutral instead of leaking a 409 conflict.
            await self.uow.rollback()
