import logging

from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PurgeOutboxEvents:
    """Retention job: drop delivered outbox rows older than the configured age."""

    def __init__(
        self,
        outbox_gateway: OutboxGateway,
        uow: UnitOfWork,
        config: OutboxConfig,
    ):
        self.outbox_gateway = outbox_gateway
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        deleted = await self.outbox_gateway.delete_published_before(
            self.config.retention_days
        )
        await self.uow.commit()
        logger.info("Outbox retention purged %d delivered event(s)", deleted)
