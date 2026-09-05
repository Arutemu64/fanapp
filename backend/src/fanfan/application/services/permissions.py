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
        permission: Permission,
    ) -> None:
        user_perm = await self.perm_gateway.get_by_permission(
            user_id=user.id,
            permission=permission,
        )
        if user_perm is not None:
            return

        # Fall back to the wildcard only when the specific grant is absent: the
        # common case (an org holding the exact permission) stays a single point
        # lookup, and a superuser holding "*" passes every check.
        wildcard = await self.perm_gateway.get_by_permission(
            user_id=user.id,
            permission=Permission.WILDCARD,
        )
        if wildcard is None:
            raise AccessDenied
