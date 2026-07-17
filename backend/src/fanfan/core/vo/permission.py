import enum
from typing import NewType
from uuid import UUID, uuid7

UserPermissionId = NewType("UserPermissionId", UUID)


def generate_user_permission_id() -> UserPermissionId:
    return UserPermissionId(uuid7())


class Permission(enum.StrEnum):
    SCHEDULE_MANAGE = "schedule:manage"
    SCHEDULE_IMPORT = "schedule:import"
    NOTIFICATIONS_SEND = "notifications:send"
    SETTINGS_MANAGE = "settings:manage"
