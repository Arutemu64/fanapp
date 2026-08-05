from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.core.models.notification import Notification


class FakeTelegramNotifier(TelegramNotifierPort):
    """Records Telegram notifications instead of calling the Bot API."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def send_notification(self, notification: Notification) -> None:
        self.sent_notifications.append(notification)


class FakePushNotifier(PushNotifierPort):
    """Records push notifications instead of sending real WebPush messages."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def send_notification(self, notification: Notification) -> None:
        self.sent_notifications.append(notification)


class FakeVkNotifier(VkNotifierPort):
    """Records VK notifications instead of calling the VK community API."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def send_notification(self, notification: Notification) -> None:
        self.sent_notifications.append(notification)
