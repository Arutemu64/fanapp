from typing import Protocol

from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.user import UserId


class UserPermissionGateway(Protocol):
    async def add(self, user_permission: UserPermission) -> None: ...

    async def delete(self, user_permission: UserPermission) -> None: ...

    async def get_by_permission(
        self,
        user_id: UserId,
        permission: Permission,
    ) -> UserPermission | None: ...

    async def get_all_for_user(self, user_id: UserId) -> list[UserPermission]: ...
