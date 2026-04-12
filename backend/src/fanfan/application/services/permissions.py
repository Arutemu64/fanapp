from fanfan.application.ports.repositories.permissions import PermissionRepository
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)


class PermissionService:
    def __init__(self, perm_repo: PermissionRepository):
        self.perm_repo = perm_repo

    async def ensure(
        self,
        user: User,
        perm_name: PermissionName,
        object_type: PermissionObjectType | None = None,
        object_id: PermissionObjectId | None = None,
    ) -> None:
        user_perm = await self.perm_repo.get(
            user_id=user.id,
            permission_name=perm_name,
            object_id=object_id,
            object_type=object_type,
        )
        if user_perm is None:
            raise AccessDenied
