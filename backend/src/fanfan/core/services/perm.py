from fanfan.adapters.db.gateways.permissions import PermissionGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.permissions import PermissionNotFound
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)


class PermService:
    def __init__(self, perm_gateway: PermissionGateway, user_gateway: UserGateway):
        self.perm_gateway = perm_gateway
        self.user_gateway = user_gateway

    async def ensure(
        self,
        user: User,
        perm_name: PermissionName,
        object_type: PermissionObjectType | None = None,
        object_id: PermissionObjectId | None = None,
    ) -> None:
        permission = await self.perm_gateway.get_permission_by_name(perm_name)
        if permission is None:
            raise PermissionNotFound
        user_perm = await self.perm_gateway.get_user_permission(
            permission_id=permission.id,
            user_id=user.id,
            object_type=object_type,
            object_id=object_id,
        )
        if user_perm is None:
            raise AccessDenied
