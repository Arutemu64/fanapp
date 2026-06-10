from fanfan.adapters.db.models import PermissionORM, UserPermissionORM
from fanfan.core.models.permission import Permission, UserPermission
from fanfan.core.vo.permission import (
    PermissionId,
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


class PermissionMapper:
    @staticmethod
    def from_model(model: Permission) -> PermissionORM:
        return PermissionORM(
            id=model.id,
            name=model.name,
        )

    @staticmethod
    def to_model(orm: PermissionORM) -> Permission:
        return Permission(
            id=PermissionId(orm.id),
            name=PermissionName(orm.name),
        )


class UserPermissionMapper:
    @staticmethod
    def from_model(model: UserPermission) -> UserPermissionORM:
        return UserPermissionORM(
            id=model.id,
            permission_id=model.permission_id,
            user_id=model.user_id,
            object_type=model.object_type,
            object_id=model.object_id,
        )

    @staticmethod
    def to_model(orm: UserPermissionORM) -> UserPermission:
        return UserPermission(
            id=UserPermissionId(orm.id),
            permission_id=PermissionId(orm.permission_id),
            user_id=UserId(orm.user_id),
            object_type=PermissionObjectType(orm.object_type)
            if orm.object_type is not None
            else None,
            object_id=PermissionObjectId(orm.object_id)
            if orm.object_id is not None
            else None,
        )
