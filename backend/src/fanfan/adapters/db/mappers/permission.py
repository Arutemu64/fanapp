from fanfan.adapters.db.models import UserPermissionORM
from fanfan.core.models.permission import UserPermission
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


class UserPermissionMapper:
    @staticmethod
    def from_model(model: UserPermission) -> UserPermissionORM:
        return UserPermissionORM(
            id=model.id,
            permission=model.permission,
            user_id=model.user_id,
            object_type=model.object_type,
            object_id=model.object_id,
        )

    @staticmethod
    def to_model(orm: UserPermissionORM) -> UserPermission:
        return UserPermission(
            id=UserPermissionId(orm.id),
            permission=PermissionName(orm.permission),
            user_id=UserId(orm.user_id),
            object_type=PermissionObjectType(orm.object_type)
            if orm.object_type is not None
            else None,
            object_id=PermissionObjectId(orm.object_id)
            if orm.object_id is not None
            else None,
        )
