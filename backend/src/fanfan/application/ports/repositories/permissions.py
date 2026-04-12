from typing import Protocol

from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)
from fanfan.core.vo.user import UserId


class PermissionRepository(Protocol):
    async def get(
        self,
        user_id: UserId,
        permission_name: PermissionName,
        object_id: PermissionObjectId | None,
        object_type: PermissionObjectType | None,
    ) -> UserPermission | None: ...
