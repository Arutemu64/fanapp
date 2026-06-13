from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class UserPermission(AggregateRoot):
    id: UserPermissionId
    permission: PermissionName
    user_id: UserId
    object_type: PermissionObjectType | None
    object_id: PermissionObjectId | None
