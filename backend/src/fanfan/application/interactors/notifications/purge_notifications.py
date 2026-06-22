import logging

from fanfan.application.interactors.notifications.config import NotificationConfig
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PurgeNotifications:
    """Retention job: drop notifications older than the configured age."""

    def __init__(
        self,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
        config: NotificationConfig,
    ):
        self.notification_gateway = notification_gateway
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        deleted = await self.notification_gateway.delete_created_before(
            self.config.retention_days
        )
        await self.uow.commit()
        logger.info(
            "Notification retention purged old notifications",
            extra={"notification_count": deleted},
        )
