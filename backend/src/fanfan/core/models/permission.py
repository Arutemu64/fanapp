from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.permission import (
    PermissionId,
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Permission:
    id: PermissionId
    name: PermissionName


@dataclass(slots=True, kw_only=True)
class UserPermission:
    id: UserPermissionId = field(default_factory=uuid7)
    permission_id: PermissionId
    user_id: UserId
    object_type: PermissionObjectType | None
    object_id: PermissionObjectId | None
