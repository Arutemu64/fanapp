from typing import Protocol

from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.user import UserId


class UserPermissionGateway(Protocol):
    async def add(self, user_permission: UserPermission) -> None: ...

    async def get_by_name(
        self,
        user_id: UserId,
        permission_name: Permission,
    ) -> UserPermission | None: ...
