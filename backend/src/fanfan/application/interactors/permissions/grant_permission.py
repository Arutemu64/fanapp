import logging

from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import Permission, generate_user_permission_id

logger = logging.getLogger(__name__)


class GrantPermission:
    """Grant one permission to a user by username.

    Deliberately unguarded: this is the bootstrap primitive that seeds the very
    first organiser's permissions, so it cannot itself require a permission
    without a chicken-and-egg. It is reachable only from the operator CLI, where
    shell access to the server is already the trust boundary. A future guarded
    caller (e.g. a web admin screen) must gate its own entry point rather than
    relying on a check here.
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
        """Return True if the grant was added, False if the user already had it."""
        user = await self.user_gateway.get_by_username(username)
        if user is None:
            raise UserNotFound

        existing = await self.perm_gateway.get_by_permission(
            user_id=user.id, permission=permission
        )
        if existing is not None:
            return False

        await self.perm_gateway.add(
            UserPermission(
                id=generate_user_permission_id(),
                permission=permission,
                user_id=user.id,
            )
        )
        await self.uow.commit()
        logger.info(
            "Permission granted",
            extra={"user_id": str(user.id), "permission": permission},
        )
        return True
