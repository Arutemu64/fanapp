from fanfan.adapters.db.models import PermissionORM, UserPermissionORM
from fanfan.core.models.permission import Permission, UserPermission


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
            id=orm.id,
            name=orm.name,
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
            id=orm.id,
            permission_id=orm.permission_id,
            user_id=orm.user_id,
            object_type=orm.object_type,
            object_id=orm.object_id,
        )
