import logging

from fanfan.application.ports.notifier import PushNotifierPort, TelegramNotifierPort
from fanfan.core.models.notification import NotificationRevocation

logger = logging.getLogger(__name__)


class RevokeNotification:
    """Recall an already-sent notification from each delivery channel.

    Mirrors SendNotification: one method per channel so the matching consumer
    can apply channel-specific retry/drop semantics.
    """

    def __init__(
        self,
        tg_notifier: TelegramNotifierPort,
        push_notifier: PushNotifierPort,
    ):
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier

    async def revoke_from_telegram(self, revocation: NotificationRevocation) -> None:
        await self.tg_notifier.revoke_notification(revocation)

    async def revoke_from_push(self, revocation: NotificationRevocation) -> None:
        await self.push_notifier.revoke_notification(revocation)
