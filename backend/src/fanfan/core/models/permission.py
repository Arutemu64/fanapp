from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.permission import (
    Permission,
    UserPermissionId,
)
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class UserPermission(AggregateRoot):
    id: UserPermissionId
    permission: Permission
    user_id: UserId
