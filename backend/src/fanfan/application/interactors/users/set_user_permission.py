import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.users import (
    CannotChangeOwnAccess,
    PermissionNotAssignable,
    UserNotFound,
)
from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class SetUserPermissionInput(BaseModel):
    user_id: UserId
    permission: Permission
    granted: bool


class SetUserPermission:
    """A superuser grants or revokes one permission of another user.

    Gated on "*" rather than users:manage: whoever may hand out permissions can
    hand themselves any of them through a second account, so only someone who
    already holds them all gets the switch. Idempotent either way.
    """

    def __init__(
        self,
        user_gateway: UserGateway,
        perm_gateway: UserPermissionGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.user_gateway = user_gateway
        self.perm_gateway = perm_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SetUserPermissionInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.WILDCARD
        )
        if data.permission is Permission.WILDCARD:
            raise PermissionNotAssignable
        if data.user_id == current_user.id:
            raise CannotChangeOwnAccess

        user = await self.user_gateway.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound

        existing = await self.perm_gateway.get_by_permission(
            user_id=user.id, permission=data.permission
        )
        if data.granted and existing is None:
            await self.perm_gateway.add(
                UserPermission(
                    id=generate_user_permission_id(),
                    permission=data.permission,
                    user_id=user.id,
                )
            )
        elif not data.granted and existing is not None:
            await self.perm_gateway.delete(existing)
        else:
            return

        await self.uow.commit()
        logger.info(
            "Permission granted" if data.granted else "Permission revoked",
            extra={
                "user_id": str(user.id),
                "actor_id": str(current_user.id),
                "permission": data.permission,
            },
        )
