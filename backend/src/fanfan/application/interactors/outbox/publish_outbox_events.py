import logging

from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PublishOutboxEvents:
    """Outbox relay: deliver pending domain events to NATS, then mark them sent.

    Runs on a short interval. At-least-once: a row is only marked published
    after NATS acks it, so a crash mid-batch just redelivers next tick.
    Consumers stay idempotent and JetStream dedups on the row id.
    """

    def __init__(
        self,
        outbox_gateway: OutboxGateway,
        events_broker: EventBroker,
        uow: UnitOfWork,
        config: OutboxConfig,
    ):
        self.outbox_gateway = outbox_gateway
        self.events_broker = events_broker
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        messages = await self.outbox_gateway.fetch_unpublished(self.config.batch_size)
        if not messages:
            return
        for message in messages:
            await self.events_broker.publish_raw(
                subject=message.subject,
                payload=message.payload,
                message_id=str(message.id),
            )
        await self.outbox_gateway.mark_published([m.id for m in messages])
        await self.uow.commit()
        logger.info("Outbox relay published %d event(s)", len(messages))
