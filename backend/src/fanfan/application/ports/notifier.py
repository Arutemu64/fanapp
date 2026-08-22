from dataclasses import dataclass
from typing import Protocol, TypeVar

from fanfan.core.models.notification import Notification
from fanfan.core.models.push_subscription import PushSubscription


# The recipient a notification resolves to on one channel. Opaque to the caller:
# the interactor only carries it from resolve() to deliver() on the same
# notifier, so each concrete shape stays private to its adapter. One dataclass
# per channel rather than a bare id keeps the channels distinct and leaves room
# to carry more per-recipient data later.
@dataclass(frozen=True, slots=True)
class TelegramTarget:
    chat_id: int


@dataclass(frozen=True, slots=True)
class VkTarget:
    peer_id: int


@dataclass(frozen=True, slots=True)
class PushTarget:
    subscriptions: list[PushSubscription]


TargetT = TypeVar("TargetT")


class Notifier(Protocol[TargetT]):
    """A notification channel, split into a DB phase and a network phase.

    Delivery is two calls on purpose so the caller can close its database
    transaction between them: ``resolve`` does the reads (who the recipient is,
    whether they are reachable), ``deliver`` does the network send. Holding a
    pooled DB connection across the send would, fanning out one mailing, pin one
    connection per in-flight notification — the reason the two are separated
    (see ``SendNotification``).
    """

    async def resolve(self, notification: Notification) -> TargetT:
        """Read the channel recipient for this notification.

        Does only DB reads — no network — so the caller may end its read
        transaction the moment this returns. Raises ``UserNotReachable`` if the
        user cannot be reached on this channel.
        """
        raise NotImplementedError

    async def deliver(self, notification: Notification, target: TargetT) -> None:
        """Send an already-resolved notification over the network.

        Runs outside the caller's read transaction: network I/O only, plus any
        self-contained follow-up write in its own short transaction (e.g. pruning
        a dead push endpoint). Raises ``UserNotReachable`` /
        ``NotificationRetryAfter`` if the send fails.
        """
        raise NotImplementedError


# Distinct Protocol types so Dishka resolves them as separate DI keys.
# Dishka strips plain Annotated metadata, so only actual types work here.
# Add a new Protocol subclass when introducing a new notification destination.
class TelegramNotifierPort(Notifier[TelegramTarget], Protocol):
    pass


class PushNotifierPort(Notifier[PushTarget], Protocol):
    pass


class VkNotifierPort(Notifier[VkTarget], Protocol):
    pass
