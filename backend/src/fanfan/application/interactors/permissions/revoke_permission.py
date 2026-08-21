import logging

from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class RevokePermission:
    """Revoke one permission from a user by username.

    Unguarded for the same bootstrap reason as GrantPermission — the operator
    CLI is the only caller and shell access is the trust boundary.
    """

    def __init__(
        self,
        user_gateway: UserGateway,
        perm_gateway: UserPermissionGateway,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.perm_gateway = perm_gateway
        self.uow = uow

    async def __call__(self, username: str, permission: Permission) -> bool:
        """Return True if a grant was removed, False if the user did not have it."""
        user = await self.user_gateway.get_by_username(username)
        if user is None:
            raise UserNotFound

        existing = await self.perm_gateway.get_by_permission(
            user_id=user.id, permission=permission
        )
        if existing is None:
            return False

        await self.perm_gateway.delete(existing)
        await self.uow.commit()
        logger.info(
            "Permission revoked",
            extra={"user_id": str(user.id), "permission": permission},
        )
        return True
