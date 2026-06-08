from abc import abstractmethod
from typing import Annotated, Protocol

from fanfan.core.models.notification import Notification


class Notifier(Protocol):
    @abstractmethod
    async def send_notification(self, notification: Notification) -> None:
        """

        :param notification:
        :raises UserNotReachable:
        :raises NotificationRetryAfter:
        """
        raise NotImplementedError


# Distinct type aliases for DI — one per delivery channel.
# Add a new alias here when introducing a new notification destination.
TelegramNotifierPort = Annotated[Notifier, "telegram"]
PushNotifierPort = Annotated[Notifier, "push"]
