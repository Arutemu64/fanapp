from typing import Protocol

from fanfan.application.dto.user import CurrentUserDTO, UserBaseDTO
from fanfan.core.vo.user import UserId, UserRole


class UserQuery(Protocol):
    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None: ...

    async def read_all_by_roles(self, *roles: UserRole) -> list[UserBaseDTO]: ...

    async def read_all_by_receive_all_announcements(self) -> list[UserBaseDTO]: ...

    async def read_schedule_editors(self) -> list[UserBaseDTO]: ...
