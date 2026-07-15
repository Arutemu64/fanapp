from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import (
    PermissionName,
)
from fanfan.core.vo.user import UserRole


class PermissionService:
    def __init__(self, perm_gateway: UserPermissionGateway):
        self.perm_gateway = perm_gateway

    async def ensure(
        self,
        user: User,
        perm_name: PermissionName,
    ) -> None:
        # ORG is the staff admin role and implicitly holds every permission,
        # so it bypasses the granular permission lookup entirely.
        if user.role is UserRole.ORG:
            return
        user_perm = await self.perm_gateway.get_by_name(
            user_id=user.id,
            permission_name=perm_name,
        )
        if user_perm is None:
            raise AccessDenied
