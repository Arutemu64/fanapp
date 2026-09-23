import logging
from datetime import timedelta
from uuid import UUID

from fanfan.application.dto.outbox import OutboxMessage
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)

# Backoff for a row whose publish failed: doubling from the base up to the cap.
# A row is never given up on — during a long NATS outage every queued row fails,
# and parking them would strand events that would have gone through once NATS
# recovered — so the cap only bounds how often a row NATS keeps rejecting costs
# a failed publish. Shape borrowed from faststream-outbox's ExponentialRetry:
# https://github.com/modern-python/faststream-outbox/blob/main/docs/operations/checklist.md
_RETRY_BASE_DELAY = timedelta(seconds=1)
_RETRY_MAX_DELAY = timedelta(minutes=5)
# The cap is reached long before this; clamping the exponent keeps a row that
# has failed for days from overflowing timedelta.
_RETRY_MAX_EXPONENT = 16
# At this attempt (~8.5 min of retrying at the delays above) the row is logged
# once at ERROR, which Sentry captures; every other failure is a WARNING.
_STUCK_AFTER_ATTEMPTS = 10


def _retry_delay(attempt: int) -> timedelta:
    exponent = min(attempt - 1, _RETRY_MAX_EXPONENT)
    multiplier: int = 2**exponent
    return min(_RETRY_BASE_DELAY * multiplier, _RETRY_MAX_DELAY)


class PublishOutboxEvents:
    """Outbox relay: deliver pending domain events to NATS, then mark them sent.

    Invoked per wake (a Postgres NOTIFY on insert, or a backstop poll tick) and
    drains the backlog to empty before returning. At-least-once: a row is only
    marked published after NATS acks it, so a crash mid-batch just redelivers on
    the next wake. Consumers stay idempotent and JetStream dedups on the row id.
    A row whose publish fails is held back with a growing delay rather than
    retried at the head of the queue, so it cannot stall the rows behind it.
    """

    def __init__(
        self,
        outbox_gateway: OutboxGateway,
        events_broker: EventBroker,
        uow: UnitOfWork,
        config: OutboxConfig,
    ) -> None:
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
            failed = False
            try:
                for message in messages:
                    try:
                        await self.events_broker.publish_raw(
                            subject=message.subject,
                            payload=message.payload,
                            message_id=str(message.id),
                        )
                    # Blind on purpose: whatever the broker raises, the row must
                    # be held back rather than left to stall the queue.
                    except Exception as error:  # noqa: BLE001
                        await self._hold_back(message, error)
                        failed = True
                        break
                    published_ids.append(message.id)
            finally:
                # Mark the delivered prefix even when the drain stops mid-batch
                # (a failed publish, or cancellation on shutdown). Otherwise the
                # already-acked rows are republished every tick, and JetStream
                # only dedups them inside its duplicate window (~2 min) — a
                # persistent failure would flood consumers with repeats.
                if published_ids:
                    await self.outbox_gateway.mark_published(published_ids)
                if published_ids or failed:
                    await self.uow.commit()
                if published_ids:
                    logger.info(
                        "Outbox relay published events",
                        extra={
                            "relay_event": "published",
                            "event_count": len(published_ids),
                        },
                    )
            if failed:
                # Stop rather than try the rest of the batch: when NATS itself is
                # down every publish fails in turn, each waiting out its timeout
                # while the batch's row locks are held. The failed row is now
                # held back, so the next wake drains the rows behind it.
                return
            if len(messages) < self.config.batch_size:
                # A short batch means the queue is drained; wait for the next
                # wake rather than spinning on empty fetches.
                return

    async def _hold_back(self, message: OutboxMessage, error: Exception) -> None:
        attempt = message.attempts + 1
        retry_in = _retry_delay(attempt)
        await self.outbox_gateway.record_failed_attempt(
            message.id, f"{type(error).__name__}: {error}", retry_in
        )
        extra = {
            "outbox_event_id": str(message.id),
            "subject": message.subject,
            "attempt": attempt,
            "retry_in_seconds": retry_in.total_seconds(),
        }
        if attempt == _STUCK_AFTER_ATTEMPTS:
            logger.error(
                "Outbox event stuck; still retrying",
                exc_info=error,
                extra={**extra, "relay_event": "publish_stuck"},
            )
        else:
            logger.warning(
                "Outbox publish failed; retry scheduled",
                exc_info=error,
                extra={**extra, "relay_event": "publish_failed"},
            )
