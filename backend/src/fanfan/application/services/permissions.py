from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    Permission,
)


class PermissionService:
    def __init__(self, perm_gateway: UserPermissionGateway) -> None:
        self.perm_gateway = perm_gateway

    async def ensure(
        self,
        user: User,
        permission: Permission,
    ) -> None:
        if not await self.has(user, permission):
            raise AccessDenied

    async def has(
        self,
        user: User,
        permission: Permission,
    ) -> bool:
        user_perm = await self.perm_gateway.get_by_permission(
            user_id=user.id,
            permission=permission,
        )
        if user_perm is not None:
            return True

        wildcard = await self.perm_gateway.get_by_permission(
            user_id=user.id,
            permission=Permission.WILDCARD,
        )
        return wildcard is not None
