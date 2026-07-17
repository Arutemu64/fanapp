from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    Permission,
)


class PermissionService:
    def __init__(self, perm_gateway: UserPermissionGateway):
        self.perm_gateway = perm_gateway

    async def ensure(
        self,
        user: User,
        perm_name: Permission,
    ) -> None:
        user_perm = await self.perm_gateway.get_by_name(
            user_id=user.id,
            permission_name=perm_name,
        )
        if user_perm is None:
            raise AccessDenied
