from typing import Protocol

from fanfan.core.models.notification import Notification


class Notifier(Protocol):
    async def send_notification(self, notification: Notification) -> None:
        """Deliver an already-persisted notification over this channel.

        The body arrives pre-sanitized (see ``HtmlSanitizer``); an adapter
        renders it for its own transport rather than re-sanitizing.

        Raises ``UserNotReachable`` when this specific recipient cannot be
        reached (blocked the bot, no push subscription) — permanent for the
        channel, so callers drop the delivery rather than retry. Raises
        ``NotificationRetryAfter`` when the transport asks for backoff, with
        the delay the caller must wait before retrying.
        """
        raise NotImplementedError


# Distinct Protocol types so Dishka resolves them as separate DI keys.
# Dishka strips plain Annotated metadata, so only actual types work here.
# Add a new Protocol subclass when introducing a new notification destination.
class TelegramNotifierPort(Notifier, Protocol):
    pass


class PushNotifierPort(Notifier, Protocol):
    pass
