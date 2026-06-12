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
    # Self-test triggered from the profile page. The service worker always shows
    # the OS-level push for this type, even when the app is visible, so the user
    # can verify push delivery without backgrounding the app.
    TEST = "test"
