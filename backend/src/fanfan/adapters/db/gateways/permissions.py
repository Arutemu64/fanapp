from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models.permission import UserPermissionORM
from fanfan.application.ports.gateways import (
    UserPermissionGateway,
)
from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    Permission,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


def _from_model(model: UserPermission) -> UserPermissionORM:
    return UserPermissionORM(
        id=model.id,
        permission=model.permission,
        user_id=model.user_id,
    )


def _to_model(orm: UserPermissionORM) -> UserPermission:
    return UserPermission(
        id=UserPermissionId(orm.id),
        permission=Permission(orm.permission),
        user_id=UserId(orm.user_id),
    )


class SqlUserPermissionGateway(UserPermissionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_permission: UserPermission) -> None:
        user_perm_orm = _from_model(user_permission)
        self.session.add(user_perm_orm)
        await self.session.flush()

    async def delete(self, user_permission: UserPermission) -> None:
        await self.session.execute(
            delete(UserPermissionORM).where(UserPermissionORM.id == user_permission.id)
        )
        await self.session.flush()

    async def get_by_permission(
        self,
        user_id: UserId,
        permission: Permission,
    ) -> UserPermission | None:
        user_perm_orm = await self.session.scalar(
            select(UserPermissionORM).where(
                and_(
                    UserPermissionORM.user_id == user_id,
                    UserPermissionORM.permission == permission,
                )
            )
        )
        return _to_model(user_perm_orm) if user_perm_orm else None

    async def get_all_for_user(self, user_id: UserId) -> list[UserPermission]:
        user_perm_orms = await self.session.scalars(
            select(UserPermissionORM)
            .where(UserPermissionORM.user_id == user_id)
            .order_by(UserPermissionORM.permission)
        )
        return [_to_model(orm) for orm in user_perm_orms]
