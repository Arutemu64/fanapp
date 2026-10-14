import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.profanity_filter import ProfanityFilter
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import UsernameProfanity
from fanfan.core.models.user import User
from fanfan.core.vo.fields import PASSWORD_FIELD, USERNAME_FIELD
from fanfan.core.vo.user import Username, UserRole, generate_user_id

logger = logging.getLogger(__name__)


class CreateUserInput(BaseModel):
    username: str = USERNAME_FIELD
    password: str = PASSWORD_FIELD
    role: UserRole


class CreateUser:
    """Create a user with a username and password.

    Deliberately unguarded, like GrantPermission: this is the bootstrap primitive
    that seeds the first organiser account before any permission exists to gate it,
    so it cannot require one without a chicken-and-egg. It is reachable only from
    the operator CLI, where shell access to the server is already the trust
    boundary. A future guarded caller (e.g. a web admin screen) must gate its own
    entry point rather than relying on a check here.
    """

    def __init__(
        self,
        user_gateway: UserGateway,
        password_hasher: PasswordHasher,
        profanity_filter: ProfanityFilter,
        uow: UnitOfWork,
    ) -> None:
        self.user_gateway = user_gateway
        self.password_hasher = password_hasher
        self.profanity_filter = profanity_filter
        self.uow = uow

    async def __call__(self, data: CreateUserInput) -> User:
        # Usernames are public, so reject profanity — same rule the self-service
        # username change enforces (UpdateCurrentUser).
        if self.profanity_filter.contains_profanity(data.username):
            raise UsernameProfanity

        user = User.create(
            id=generate_user_id(),
            username=Username(data.username),
            hashed_password=self.password_hasher.hash(data.password),
            role=data.role,
        )
        # A taken username surfaces as UserAlreadyExists from the gateway's unique
        # constraint translation — no pre-check, so a concurrent insert can't slip
        # between a check and the write.
        await self.user_gateway.add(user)
        await self.uow.commit()
        logger.info(
            "User created",
            extra={"user_id": str(user.id), "role": user.role},
        )
        return user
