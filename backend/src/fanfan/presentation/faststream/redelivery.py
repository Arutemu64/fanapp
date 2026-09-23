import dataclasses
import logging
from types import TracebackType

from faststream import BaseMiddleware
from faststream.exceptions import HandlerException
from faststream.nats import NatsBroker
from faststream.nats.subscriber import LogicSubscriber
from nats.aio.msg import Msg
from nats.errors import Error as NatsError
from nats.js.api import ConsumerConfig

logger = logging.getLogger(__name__)

# Deliveries (the first one included) before a failing message is given up on.
# JetStream's default is unlimited and a plain nak redelivers immediately, so a
# message that always fails would otherwise loop hot forever
# (https://docs.nats.io/learn/jetstream/acknowledgment). The middleware below
# terms at this count; the consumer carries it too, so the server also stops
# when a handler hangs past AckWait instead of raising. Generous because the
# send consumers spend deliveries on Telegram/VK flood-control retry-afters.
MAX_DELIVER = 20

# Delay before each redelivery, by deliveries so far; the last one repeats.
# Sent with the nak rather than set as the consumer's BackOff: NATS applies
# BackOff only to AckWait expiry, never to a nak, and setting it replaces
# AckWait with its first step — which would cut the send consumers' 90 s
# AckWait to one second.
_REDELIVERY_DELAYS_SECONDS = (1, 5, 30, 120, 300)


def consumer_config(*, ack_wait: float | None = None) -> ConsumerConfig:
    """The ConsumerConfig every durable subscriber is declared with."""
    return ConsumerConfig(max_deliver=MAX_DELIVER, ack_wait=ack_wait)


def _redelivery_delay(deliveries: int) -> int:
    index = min(deliveries, len(_REDELIVERY_DELAYS_SECONDS)) - 1
    return _REDELIVERY_DELAYS_SECONDS[index]


class RedeliveryMiddleware(BaseMiddleware):
    """Turn a handler's unhandled error into a delayed, bounded redelivery.

    Runs before FastStream's ack policy (broker middlewares exit first), so the
    ack policy then finds the message already settled and leaves it alone. A
    handler that settled the message itself, or raised FastStream's own
    Ack/Nack/RejectMessage, is left to that decision.
    """

    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool | None:
        is_unhandled = isinstance(exc_val, Exception) and not isinstance(
            exc_val, HandlerException
        )
        if is_unhandled:
            await self._settle_failed()
        return await super().after_processed(exc_type, exc_val, exc_tb)

    async def _settle_failed(self) -> None:
        msg = self.msg
        # Only a JetStream delivery can be redelivered or carries a count.
        if not isinstance(msg, Msg) or not msg.reply or msg.is_acked:
            return
        if not msg.reply.startswith("$JS.ACK."):
            return
        deliveries = msg.metadata.num_delivered
        try:
            if deliveries >= MAX_DELIVER:
                logger.error(
                    "Message dropped after max deliveries",
                    extra={"subject": msg.subject, "deliveries": deliveries},
                )
                await msg.term()
                return
            await msg.nak(delay=_redelivery_delay(deliveries))
        except NatsError:
            # The ack could not reach NATS; with the message unsettled the
            # server redelivers it after AckWait anyway, so this only costs time.
            logger.warning("Could not settle a failed message", exc_info=True)


async def sync_consumer_configs(broker: NatsBroker) -> None:
    """Push each durable subscriber's declared config to the server.

    nats-py sends a ConsumerConfig only when it creates a durable; an existing
    durable keeps its first config, and the NATS data volume outlives deploys.
    A same-name add_consumer updates the editable fields (max_deliver,
    ack_wait, …) in place, so a changed declaration reaches production.
    """
    js = broker.connection.jetstream()
    for subscriber in broker.subscribers:
        declared = getattr(subscriber, "config", None)
        stream = getattr(subscriber, "stream", None)
        if not isinstance(subscriber, LogicSubscriber) or stream is None:
            continue
        if not isinstance(declared, ConsumerConfig) or declared.durable_name is None:
            continue
        # The filter must be spelled out: nats-py fills it in only on create,
        # and an update without one would widen the durable to every subject
        # in the stream.
        config = dataclasses.replace(
            declared,
            name=declared.durable_name,
            filter_subject=subscriber.subject.template,
        )
        try:
            await js.add_consumer(stream.name, config=config)
        except NatsError:
            # A non-editable field changed, or NATS did not answer; the durable
            # keeps working with its old config, so report it rather than block
            # startup.
            logger.warning(
                "Could not update consumer config",
                extra={"durable": declared.durable_name},
                exc_info=True,
            )
