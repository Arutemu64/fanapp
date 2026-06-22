from fanfan.application.ports.notifier import PushNotifierPort, TelegramNotifierPort
from fanfan.core.models.notification import Notification, NotificationRevocation


class FakeTelegramNotifier(TelegramNotifierPort):
    """Records Telegram notifications instead of calling the Bot API."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []
        self.revocations: list[NotificationRevocation] = []

    async def send_notification(self, notification: Notification) -> None:
        self.sent_notifications.append(notification)

    async def revoke_notification(self, revocation: NotificationRevocation) -> None:
        self.revocations.append(revocation)


class FakePushNotifier(PushNotifierPort):
    """Records push notifications instead of sending real WebPush messages."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []
        self.revocations: list[NotificationRevocation] = []

    async def send_notification(self, notification: Notification) -> None:
        self.sent_notifications.append(notification)

    async def revoke_notification(self, revocation: NotificationRevocation) -> None:
        self.revocations.append(revocation)
