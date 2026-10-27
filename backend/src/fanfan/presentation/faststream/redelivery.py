import asyncio
import contextlib
import dataclasses
import logging
from collections.abc import AsyncGenerator
from types import TracebackType
from typing import override

from faststream import BaseMiddleware
from faststream.exceptions import HandlerException
from faststream.nats import NatsBroker, NatsMessage
from faststream.nats.subscriber import LogicSubscriber
from nats.aio.msg import Msg
from nats.errors import Error as NatsError
from nats.js.api import ConsumerConfig
from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)

MAX_DELIVER = 20

_REDELIVERY_DELAYS_SECONDS = (1, 5, 30, 120, 300)


_IN_PROGRESS_INTERVAL_SECONDS = 10.0


def consumer_config(*, ack_wait: float | None = None) -> ConsumerConfig:
    """The ConsumerConfig every durable subscriber is declared with."""
    return ConsumerConfig(max_deliver=MAX_DELIVER, ack_wait=ack_wait)


@contextlib.asynccontextmanager
async def in_progress_heartbeat(
    msg: NatsMessage, interval: float = _IN_PROGRESS_INTERVAL_SECONDS
) -> AsyncGenerator[None]:
    """Keep a long handler's message from being redelivered while it runs.

    An in-progress ack resets the AckWait timer
    (https://docs.nats.io/learn/jetstream/acknowledgment), so a slow but live
    handler is not redelivered to another worker mid-run. It only saves wasted
    redeliveries; it cannot prove the worker is alive (a beat can be lost), so a
    handler that must not run twice also takes a WorkerLock.
    """

    async def beat() -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await msg.in_progress()
            except NatsError:
                logger.warning("Could not extend a message's AckWait", exc_info=True)

    task = asyncio.create_task(beat())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def is_last_delivery(msg: Msg) -> bool:
    """Whether a failure now ends this message: RedeliveryMiddleware terms it.

    A handler whose message carries work nothing else retries checks this to
    settle that work as failed before it is dropped.
    """
    if not msg.reply.startswith("$JS.ACK."):
        return False
    return msg.metadata.num_delivered >= MAX_DELIVER


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

    @override
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
        if not isinstance(msg, Msg) or not msg.reply or msg.is_acked:
            return
        if not msg.reply.startswith("$JS.ACK."):
            return
        deliveries = msg.metadata.num_delivered
        try:
            if is_last_delivery(msg):
                logger.error(
                    "Message dropped after max deliveries",
                    extra={"subject": msg.subject, "deliveries": deliveries},
                )
                await msg.term()
                return
            await msg.nak(delay=_redelivery_delay(deliveries))
        except NatsError:
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
        config = dataclasses.replace(
            declared,
            name=declared.durable_name,
            filter_subject=subscriber.subject.template,
        )
        await _apply_consumer_config(js, stream.name, declared.durable_name, config)


async def _apply_consumer_config(
    js: JetStreamContext, stream_name: str, durable: str, config: ConsumerConfig
) -> None:
    try:
        current = await js.consumer_info(stream_name, durable)
    except NatsError:
        current = None
    try:
        await js.add_consumer(stream_name, config=config)
    except NatsError:
        logger.warning(
            "Could not update consumer config",
            extra={"durable": durable},
            exc_info=True,
        )
        return
    if current is None:
        return
    changed = changed_consumer_fields(current.config, config)
    if changed:
        logger.info(
            "Consumer config updated",
            extra={"durable": durable, "changed_fields": ",".join(changed)},
        )


def changed_consumer_fields(
    current: ConsumerConfig, declared: ConsumerConfig
) -> list[str]:
    """The fields the declaration sets that differ from the server's config."""
    changed: list[str] = []
    for field in dataclasses.fields(declared):
        wanted = getattr(declared, field.name)
        if wanted is None:
            continue
        if getattr(current, field.name) != wanted:
            changed.append(field.name)
    return changed
