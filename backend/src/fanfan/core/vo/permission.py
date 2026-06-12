import enum
from typing import NewType
from uuid import UUID, uuid7

PermissionId = NewType("PermissionId", int)
PermissionName = NewType("PermissionName", str)
UserPermissionId = NewType("UserPermissionId", UUID)
PermissionObjectType = NewType("PermissionObjectType", str)
PermissionObjectId = NewType("PermissionObjectId", int)


def generate_user_permission_id() -> UserPermissionId:
    return UserPermissionId(uuid7())


class Permissions(enum.StrEnum):
    SCHEDULE_MANAGE = "schedule:manage"
    SCHEDULE_IMPORT = "schedule:import"
    NOTIFICATIONS_SEND = "notifications:send"
    SETTINGS_MANAGE = "settings:manage"
