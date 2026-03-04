import enum
from typing import NewType
from uuid import UUID

PermissionId = NewType("PermissionId", int)
PermissionName = NewType("PermissionName", str)
UserPermissionId = NewType("UserPermissionId", UUID)
PermissionObjectType = NewType("PermissionObjectType", str)
PermissionObjectId = NewType("PermissionObjectId", int)


class Permissions(enum.StrEnum):
    SCHEDULE_MANAGE = "schedule:manage"
