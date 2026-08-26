import logging
from uuid import UUID

from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PublishOutboxEvents:
    """Outbox relay: deliver pending domain events to NATS, then mark them sent.

    Invoked per wake (a Postgres NOTIFY on insert, or a backstop poll tick) and
    drains the backlog to empty before returning. At-least-once: a row is only
    marked published after NATS acks it, so a crash mid-batch just redelivers on
    the next wake. Consumers stay idempotent and JetStream dedups on the row id.
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
        # Drain the whole backlog per wake, not just one batch: a single wake
        # (a NOTIFY, or a backstop tick) must catch up however many rows are
        # queued. Otherwise a burst larger than batch_size would trickle out one
        # batch per poll interval, since with LISTEN/NOTIFY a coalesced wake
        # fires the relay only once. Each batch commits (releasing its row locks)
        # before the next is fetched, so this is bounded work per batch, not one
        # growing transaction. The loop ends when a fetch returns a short batch.
        while True:
            messages = await self.outbox_gateway.fetch_unpublished(
                self.config.batch_size
            )
            if not messages:
                return
            published_ids: list[UUID] = []
            try:
                for message in messages:
                    await self.events_broker.publish_raw(
                        subject=message.subject,
                        payload=message.payload,
                        message_id=str(message.id),
                    )
                    published_ids.append(message.id)
            finally:
                # Mark the delivered prefix even when a publish fails mid-batch.
                # Otherwise the already-acked rows are republished every tick, and
                # JetStream only dedups them inside its duplicate window (~2 min) —
                # a persistent failure would flood consumers with repeats.
                if published_ids:
                    await self.outbox_gateway.mark_published(published_ids)
                    await self.uow.commit()
                    logger.info(
                        "Outbox relay published events",
                        extra={"event_count": len(published_ids)},
                    )
            if len(messages) < self.config.batch_size:
                # A short batch means the queue is drained; wait for the next
                # wake rather than spinning on empty fetches.
                return
