from typing import Protocol

from fanfan.core.models.notification import Notification, NotificationRevocation


class Notifier(Protocol):
    async def send_notification(self, notification: Notification) -> None:
        """

        :param notification:
        :raises UserNotReachable:
        :raises NotificationRetryAfter:
        """
        raise NotImplementedError

    async def revoke_notification(self, revocation: NotificationRevocation) -> None:
        """Recall an already-sent notification from this channel (best-effort).

        Implementations must treat an already-gone message as success (nothing
        to do), not an error.

        :param revocation:
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
