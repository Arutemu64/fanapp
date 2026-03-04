from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.permission import PermissionMapper, UserPermissionMapper
from fanfan.adapters.db.models.permission import PermissionORM, UserPermissionORM
from fanfan.core.models.permission import Permission, UserPermission
from fanfan.core.vo.permission import PermissionName
from fanfan.core.vo.user import UserId


class PermissionGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.permission_mapper = PermissionMapper()
        self.user_permission_mapper = UserPermissionMapper()

    async def add_permission(self, permission: Permission) -> Permission:
        permission_orm = self.permission_mapper.from_model(permission)
        self.session.add(permission_orm)
        await self.session.flush([permission_orm])
        return self.permission_mapper.to_model(permission_orm)

    async def add_user_permission(self, user_perm: UserPermission) -> UserPermission:
        user_perm_orm = self.user_permission_mapper.from_model(user_perm)
        self.session.add(user_perm_orm)
        await self.session.flush([user_perm_orm])
        return self.user_permission_mapper.to_model(user_perm_orm)

    async def get_permission_by_name(self, name: PermissionName) -> Permission | None:
        permission_orm = await self.session.scalar(
            select(PermissionORM).where(PermissionORM.name == name)
        )
        return (
            self.permission_mapper.to_model(permission_orm) if permission_orm else None
        )

    async def get_user_permission(
        self,
        user_id: UserId,
        permission_name: PermissionName,
        object_id: int | None,
        object_type: str | None,
    ) -> UserPermission | None:
        user_perm_orm = await self.session.scalar(
            select(UserPermissionORM)
            .join(PermissionORM)
            .where(
                and_(
                    UserPermissionORM.user_id == user_id,
                    PermissionORM.name == permission_name,
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
