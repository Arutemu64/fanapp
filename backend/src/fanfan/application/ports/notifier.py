from abc import abstractmethod
from typing import Protocol

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


# Distinct Protocol types so Dishka resolves them as separate DI keys.
# Dishka strips plain Annotated metadata, so only actual types work here.
# Add a new Protocol subclass when introducing a new notification destination.
class TelegramNotifierPort(Notifier, Protocol):
    pass


class PushNotifierPort(Notifier, Protocol):
    pass
