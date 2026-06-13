from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.permission import UserPermissionMapper
from fanfan.adapters.db.models.permission import UserPermissionORM
from fanfan.application.ports.gateways import (
    UserPermissionGateway,
)
from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)
from fanfan.core.vo.user import UserId


class SqlUserPermissionGateway(UserPermissionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_permission_mapper = UserPermissionMapper()

    async def add(self, user_permission: UserPermission) -> None:
        user_perm_orm = self.user_permission_mapper.from_model(user_permission)
        self.session.add(user_perm_orm)
        await self.session.flush()

    async def get_by_name(
        self,
        user_id: UserId,
        permission_name: PermissionName,
        object_id: PermissionObjectId | None,
        object_type: PermissionObjectType | None,
    ) -> UserPermission | None:
        user_perm_orm = await self.session.scalar(
            select(UserPermissionORM).where(
                and_(
                    UserPermissionORM.user_id == user_id,
                    UserPermissionORM.permission == permission_name,
                    UserPermissionORM.object_id == object_id,
                    UserPermissionORM.object_type == object_type,
                )
            )
        )
        return (
            self.user_permission_mapper.to_model(user_perm_orm)
            if user_perm_orm
            else None
        )
