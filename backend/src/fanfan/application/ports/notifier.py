from typing import Protocol

from fanfan.core.models.notification import Notification


class Notifier(Protocol):
    async def send_notification(self, notification: Notification) -> None:
        """Deliver notification, raising UserNotReachable if the user cannot be
        reached or NotificationRetryAfter if delivery should be retried later.
        """
        raise NotImplementedError


# Distinct Protocol types so Dishka resolves them as separate DI keys.
# Dishka strips plain Annotated metadata, so only actual types work here.
# Add a new Protocol subclass when introducing a new notification destination.
class TelegramNotifierPort(Notifier, Protocol):
    pass


class PushNotifierPort(Notifier, Protocol):
    pass


class VkNotifierPort(Notifier, Protocol):
    pass
