from enum import StrEnum
from typing import NewType
from uuid import UUID, uuid7

NotificationId = NewType("NotificationId", UUID)


def generate_notification_id() -> NotificationId:
    return NotificationId(uuid7())


class NotificationType(StrEnum):
    DEFAULT = "default"
    SCHEDULE_CHANGE = "schedule_change"
    SCHEDULE_SUBSCRIPTION = "schedule_subscription"
    MESSAGE = "message"
    POINTS_RECEIVED = "points_received"
    BROADCAST = "broadcast"
