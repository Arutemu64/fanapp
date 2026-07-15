from typing import Protocol

from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagName


class UserFlagGateway(Protocol):
    async def add(self, flag: UserFlag) -> None: ...
    async def get_by_user(
        self, user_id: UserId, flag_name: UserFlagName
    ) -> UserFlag | None: ...
    async def delete(self, flag: UserFlag) -> None: ...
