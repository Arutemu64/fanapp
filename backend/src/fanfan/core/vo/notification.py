from enum import StrEnum
from typing import NewType
from uuid import UUID

NotificationId = NewType("NotificationId", UUID)


class NotificationType(StrEnum):
    DEFAULT = "default"
    SCHEDULE_CHANGE = "schedule_change"
    SCHEDULE_SUBSCRIPTION = "schedule_subscription"
    MESSAGE = "message"
    POINTS_RECEIVED = "points_received"
