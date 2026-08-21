from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.permission import Permission


class ListUserPermissions:
    """List the permissions currently granted to a user by username."""

    def __init__(
        self,
        user_gateway: UserGateway,
        perm_gateway: UserPermissionGateway,
    ):
        self.user_gateway = user_gateway
        self.perm_gateway = perm_gateway

    async def __call__(self, username: str) -> list[Permission]:
        user = await self.user_gateway.get_by_username(username)
        if user is None:
            raise UserNotFound

        user_perms = await self.perm_gateway.get_all_for_user(user.id)
        return [user_perm.permission for user_perm in user_perms]
