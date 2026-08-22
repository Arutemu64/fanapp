from fanfan.application.ports.notifier import (
    PushNotifierPort,
    PushTarget,
    TelegramNotifierPort,
    TelegramTarget,
    VkNotifierPort,
    VkTarget,
)
from fanfan.core.models.notification import Notification


class FakeTelegramNotifier(TelegramNotifierPort):
    """Records Telegram notifications instead of calling the Bot API."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def resolve(
        self,
        notification: Notification,  # noqa: ARG002  # part of the port contract
    ) -> TelegramTarget:
        return TelegramTarget(chat_id=0)

    async def deliver(
        self,
        notification: Notification,
        target: TelegramTarget,  # noqa: ARG002  # part of the port contract
    ) -> None:
        self.sent_notifications.append(notification)


class FakePushNotifier(PushNotifierPort):
    """Records push notifications instead of sending real WebPush messages."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def resolve(
        self,
        notification: Notification,  # noqa: ARG002  # part of the port contract
    ) -> PushTarget:
        return PushTarget(subscriptions=[])

    async def deliver(
        self,
        notification: Notification,
        target: PushTarget,  # noqa: ARG002  # part of the port contract
    ) -> None:
        self.sent_notifications.append(notification)


class FakeVkNotifier(VkNotifierPort):
    """Records VK notifications instead of calling the VK community API."""

    def __init__(self) -> None:
        self.sent_notifications: list[Notification] = []

    async def resolve(
        self,
        notification: Notification,  # noqa: ARG002  # part of the port contract
    ) -> VkTarget:
        return VkTarget(peer_id=0)

    async def deliver(
        self,
        notification: Notification,
        target: VkTarget,  # noqa: ARG002  # part of the port contract
    ) -> None:
        self.sent_notifications.append(notification)
