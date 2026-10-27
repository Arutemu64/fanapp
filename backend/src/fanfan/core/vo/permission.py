import enum
from typing import NewType
from uuid import UUID, uuid7

UserPermissionId = NewType("UserPermissionId", UUID)


def generate_user_permission_id() -> UserPermissionId:
    return UserPermissionId(uuid7())


class Permission(enum.StrEnum):
    WILDCARD = "*"
    SCHEDULE_MANAGE = "schedule:manage"
    SCHEDULE_SETUP = "schedule:setup"
    NOTIFICATIONS_SEND = "notifications:send"
    SETTINGS_MANAGE = "settings:manage"
    TICKETS_MANAGE = "tickets:manage"
    SYNC_RUN = "sync:run"
    DEMO_SEED = "demo:seed"
    FEEDBACK_READ = "feedback:read"
    VOTING_MANAGE = "voting:manage"
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    QUEST_AWARD = "quest:award"
    QUEST_MANAGE = "quest:manage"
