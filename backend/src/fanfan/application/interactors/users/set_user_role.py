import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.users import CannotChangeOwnAccess, UserNotFound
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId, UserRole

logger = logging.getLogger(__name__)


class SetUserRoleInput(BaseModel):
    user_id: UserId
    role: UserRole


class SetUserRole:
    """An organizer changes another user's role (users:manage).

    The role only decides which sections a user sees; every organizer action
    stays behind its own permission, so this cannot grant one.
    """

    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SetUserRoleInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_MANAGE
        )
        if data.user_id == current_user.id:
            raise CannotChangeOwnAccess

        user = await self.user_gateway.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        previous_role = user.role
        user.set_role(data.role)
        await self.user_gateway.save(user)
        await self.uow.commit()
        logger.info(
            "User role changed",
            extra={
                "user_id": str(user.id),
                "actor_id": str(current_user.id),
                "previous_role": previous_role,
                "role": data.role,
            },
        )
