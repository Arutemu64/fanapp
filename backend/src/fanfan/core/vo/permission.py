import enum
from typing import NewType
from uuid import UUID, uuid7

PermissionName = NewType("PermissionName", str)
UserPermissionId = NewType("UserPermissionId", UUID)


def generate_user_permission_id() -> UserPermissionId:
    return UserPermissionId(uuid7())


class Permissions(enum.StrEnum):
    SCHEDULE_MANAGE = "schedule:manage"
    SCHEDULE_IMPORT = "schedule:import"
    NOTIFICATIONS_SEND = "notifications:send"
    SETTINGS_MANAGE = "settings:manage"
