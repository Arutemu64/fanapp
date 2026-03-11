from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UsernameAlreadyTaken, UserNotFound
from fanfan.core.models.user import User
from fanfan.core.vo.fields import USERNAME_PATTERN
from fanfan.core.vo.user import UserId, UserRole

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ChangeUserRoleRequest:
    user_id: UserId
    role: UserRole


class UpdateCurrentUserCommand(BaseModel):
    username: str | None = Field(
        None, min_length=3, max_length=25, pattern=USERNAME_PATTERN
    )
    first_name: str | None = Field(None, max_length=50)


class UpdateCurrentUser:
    def __init__(
        self, id_provider: IdProvider, uow: UnitOfWork, user_gateway: UserGateway
    ) -> None:
        self.id_provider = id_provider
        self.user_gateway = user_gateway
        self.uow = uow

    async def _update_username(
        self, current_user: User, new_username: str | None
    ) -> None:
        if new_username:
            user = await self.user_gateway.get_user_by_username(new_username)
            if user and (current_user.id != user.id):
                raise UsernameAlreadyTaken
        current_user.username = new_username

    async def __call__(self, data: UpdateCurrentUserCommand):
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
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
                current_user.first_name = data_to_update["first_name"]
                user_updated_flag = True
            if user_updated_flag:
                await self.user_gateway.save_user(current_user)
                await self.uow.commit()
