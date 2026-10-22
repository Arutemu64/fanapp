import enum
from typing import NewType
from uuid import UUID, uuid7

UserPermissionId = NewType("UserPermissionId", UUID)


def generate_user_permission_id() -> UserPermissionId:
    return UserPermissionId(uuid7())


class Permission(enum.StrEnum):
    # Superuser grant: a user holding it satisfies every ensure() check, so one
    # grant covers all organizer surfaces (bootstrap, dev, single-admin deploys).
    # It is a real, storable member — grantable/revocable through the same CLI,
    # gateway and CHECK constraint as any other — and the wildcard only short-
    # circuits at check time (PermissionService.ensure, frontend hasPermission);
    # nothing here expands audience queries that filter on a specific permission.
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
