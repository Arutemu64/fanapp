import logging

from pydantic import MISSING, BaseModel, Field

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.profanity_filter import ProfanityFilter
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import UsernameAlreadyTaken, UsernameProfanity
from fanfan.core.models.user import User
from fanfan.core.vo.fields import USERNAME_PATTERN
from fanfan.core.vo.user import AVATAR_SEED_PATTERN, Username

logger = logging.getLogger(__name__)


class UpdateCurrentUserInput(BaseModel):
    # MISSING rather than None, like UpdateAppSettingsInput: neither can be
    # cleared, so an explicit null is a 422 rather than a silent no-op, and the
    # patterns already turn away an empty string.
    username: str | MISSING = Field(
        default=MISSING, min_length=3, max_length=25, pattern=USERNAME_PATTERN
    )
    # Proposed by the client so the profile editor can preview a face before
    # saving; the pattern keeps it to a harmless token.
    avatar_seed: str | MISSING = Field(default=MISSING, pattern=AVATAR_SEED_PATTERN)


class UpdateCurrentUser:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
        user_gateway: UserGateway,
        profanity_filter: ProfanityFilter,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.user_gateway = user_gateway
        self.uow = uow
        self.profanity_filter = profanity_filter

    async def _update_username(self, current_user: User, new_username: str) -> None:
        # Usernames are public, so reject profanity. Checked here rather than in
        # the input schema because the matching logic lives behind a port.
        if self.profanity_filter.contains_profanity(new_username):
            raise UsernameProfanity
        user = await self.user_gateway.get_by_username(new_username)
        if user and (current_user.id != user.id):
            raise UsernameAlreadyTaken
        current_user.set_username(Username(new_username))

    async def __call__(self, data: UpdateCurrentUserInput) -> None:
        current_user = await self.current_user_provider.require_user()
        user_updated_flag = False
        if data.username is not MISSING and data.username != current_user.username:
            await self._update_username(current_user, data.username)
            user_updated_flag = True
        if (
            data.avatar_seed is not MISSING
            and data.avatar_seed != current_user.avatar_seed
        ):
            current_user.set_avatar_seed(data.avatar_seed)
            user_updated_flag = True
        if user_updated_flag:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
