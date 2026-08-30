from typing import Protocol

from fanfan.core.models.notification import Notification


class Notifier(Protocol):
    async def send_notification(self, notification: Notification) -> None:
        """Deliver the notification, or raise one of the contract's exceptions:

        - ``UserNotReachable`` — this user cannot be reached on this channel
          (opted out, not linked, or the provider refused delivery to them).
        - ``NotificationRetryAfter`` — a transient failure; retry after the hint.
        - ``NotificationChannelUnavailable`` — the whole channel is misconfigured
          (bad token, missing VAPID keys); retrying cannot help, so drop it.
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
