import logging

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import UsernameAlreadyTaken
from fanfan.core.models.user import User
from fanfan.core.vo.fields import USERNAME_PATTERN
from fanfan.core.vo.user import Username

logger = logging.getLogger(__name__)


class UpdateCurrentUserInput(BaseModel):
    username: str | None = Field(
        None, min_length=3, max_length=25, pattern=USERNAME_PATTERN
    )
    first_name: str | None = Field(None, max_length=50)


class UpdateCurrentUser:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
        user_gateway: UserGateway,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.user_gateway = user_gateway
        self.uow = uow

    async def _update_username(
        self, current_user: User, new_username: str | None
    ) -> None:
        if new_username:
            user = await self.user_gateway.get_by_username(new_username)
            if user and (current_user.id != user.id):
                raise UsernameAlreadyTaken
            current_user.set_username(Username(new_username))
        else:
            current_user.set_username(None)

    async def __call__(self, data: UpdateCurrentUserInput) -> None:
        current_user = await self.current_user_provider.require_user()
        data_to_update = data.model_dump(exclude_unset=True)
        user_updated_flag = False
        if (
            "username" in data_to_update
            and data_to_update["username"] != current_user.username
        ):
            await self._update_username(current_user, data_to_update["username"])
            user_updated_flag = True
        if (
            "first_name" in data_to_update
            and data_to_update["first_name"] != current_user.first_name
        ):
            current_user.set_first_name(data_to_update["first_name"])
            user_updated_flag = True
        if user_updated_flag:
            await self.user_gateway.save(current_user)
            await self.uow.commit()
