import logging
from typing import Annotated

from pydantic import MISSING, Field

from fanfan.application.dto.input import InputModel
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.profanity_filter import ProfanityFilter
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import UsernameAlreadyTaken, UsernameProfanity
from fanfan.core.models.user import User
from fanfan.core.vo.fields import USERNAME_PATTERN
from fanfan.core.vo.user import AVATAR_SEED_PATTERN, Username

logger = logging.getLogger(__name__)


class UpdateCurrentUserInput(InputModel):
    username: (
        Annotated[str, Field(min_length=3, max_length=25, pattern=USERNAME_PATTERN)]
        | MISSING
    ) = MISSING
    avatar_seed: Annotated[str, Field(pattern=AVATAR_SEED_PATTERN)] | MISSING = MISSING


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
        if self.profanity_filter.contains_profanity(new_username):
            raise UsernameProfanity
        user = await self.user_gateway.get_by_username(new_username)
        if user and (current_user.id != user.id):
            raise UsernameAlreadyTaken
        current_user.set_username(Username(new_username))

    async def __call__(self, data: UpdateCurrentUserInput) -> None:
        current_user = await self.current_user_provider.require_user()
        data_to_update = data.model_dump(exclude_unset=True)
        user_updated_flag = False
        if (
            data_to_update.get("username")
            and data_to_update["username"] != current_user.username
        ):
            await self._update_username(current_user, data_to_update["username"])
            user_updated_flag = True
        avatar_seed = data_to_update.get("avatar_seed")
        if avatar_seed and avatar_seed != current_user.avatar_seed:
            current_user.set_avatar_seed(avatar_seed)
            user_updated_flag = True
        if user_updated_flag:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
