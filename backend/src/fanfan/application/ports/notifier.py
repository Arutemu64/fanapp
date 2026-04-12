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
