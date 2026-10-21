import asyncio
import contextlib
import json
import logging
import random
from collections.abc import AsyncIterator
from typing import Any

from adaptix import Retort
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

BROADCAST_CHANNEL = "sse:broadcast"
USER_CHANNEL_PREFIX = "sse:user:"

# Cap per-connection buffering so a slow/stuck SSE client cannot grow memory
# without bound. On overflow we drop the oldest message to favour freshness.
SSE_QUEUE_MAXSIZE = 100

# An idle pub/sub socket can die silently (NAT idle timeout, firewall drop)
# without ever reporting an error, which would leave every open stream deaf
# until a restart. After this long without traffic the reader pings, and a ping
# still unanswered one interval later counts as a dropped connection.
_HEALTH_CHECK_INTERVAL_SECONDS = 30.0

# Reconnect delay after the subscription fails: exponential with jitter, so a
# Valkey outage is retried at a falling rate instead of logging every second.
_RECONNECT_BASE_DELAY_SECONDS = 0.5
_RECONNECT_MAX_DELAY_SECONDS = 30.0
_RECONNECT_MAX_EXPONENT = 16


def _reconnect_delay(failures: int) -> float:
    # Clamp the exponent: the cap is hit after a handful of failures, and an
    # unclamped power overflows float once a long outage piles up ~1000 of them.
    exponent = min(failures - 1, _RECONNECT_MAX_EXPONENT)
    multiplier: int = 2**exponent
    delay = _RECONNECT_BASE_DELAY_SECONDS * multiplier
    jitter = random.uniform(0.5, 1.5)  # noqa: S311 - not security-sensitive
    return min(delay * jitter, _RECONNECT_MAX_DELAY_SECONDS)


def _offer(
    queue: asyncio.Queue[SSEMessage], message: SSEMessage, user_id: UserId | None
) -> None:
    # Slow consumer: drop the oldest to make room for the newest.
    # No lock needed — asyncio runs this without interruption.
    if queue.full():
        queue.get_nowait()
        logger.warning(
            "SSE queue full, dropped oldest message",
            extra={
                "user_id": str(user_id) if user_id else None,
                "event_name": message.event_name,
            },
        )

    queue.put_nowait(message)


class ValkeyRealtimeGateway(RealtimeGateway):
    """Live SSE messages over Valkey pub/sub.

    At-most-once, like the SSE stream itself: a message published while a
    process is reconnecting is lost, which is acceptable because every SSE
    event only tells clients to refetch state the API already holds
    (https://valkey.io/topics/pubsub/).

    One process-wide reader holds a single pub/sub connection — the broadcast
    channel plus a pattern over every user channel — and fans each message out
    to the open streams in memory, instead of a connection per open stream.
    Every process thus receives every user's messages and drops those for users
    with no stream here; at this app's scale that is far cheaper than a
    subscribe and unsubscribe round-trip per stream. Relies on APP scope
    (main/ioc/redis.py): one gateway per process.
    """

    def __init__(self, redis: Redis, retort: Retort) -> None:
        self.redis = redis
        self.retort = retort
        # Every open stream's queue, mapped to its user for the overflow log.
        self._queues: dict[asyncio.Queue[SSEMessage], UserId | None] = {}
        self._queues_by_user: dict[str, set[asyncio.Queue[SSEMessage]]] = {}
        self._reader: asyncio.Task[None] | None = None

    async def publish(self, message: SSEMessage, user_id: UserId | None = None) -> None:
        channel = BROADCAST_CHANNEL
        if user_id:
            channel = f"{USER_CHANNEL_PREFIX}{user_id}"
        await self.redis.publish(channel, json.dumps(self.retort.dump(message)))

    def subscribe(self, user_id: UserId | None = None) -> AsyncIterator[SSEMessage]:
        async def iterator() -> AsyncIterator[SSEMessage]:
            queue: asyncio.Queue[SSEMessage] = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)
            self._ensure_reader()
            self._attach(queue, user_id)
            logger.info(
                "Realtime subscriptions attached",
                extra={
                    "authenticated": user_id is not None,
                    "user_id": str(user_id) if user_id else None,
                },
            )
            try:
                while True:
                    yield await queue.get()
            finally:
                self._detach(queue, user_id)
                logger.info(
                    "Realtime subscriptions closed",
                    extra={
                        "authenticated": user_id is not None,
                        "user_id": str(user_id) if user_id else None,
                    },
                )

        return iterator()

    async def close(self) -> None:
        if self._reader is None:
            return
        self._reader.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._reader
        self._reader = None

    def _attach(self, queue: asyncio.Queue[SSEMessage], user_id: UserId | None) -> None:
        self._queues[queue] = user_id
        if user_id:
            self._queues_by_user.setdefault(str(user_id), set()).add(queue)

    def _detach(self, queue: asyncio.Queue[SSEMessage], user_id: UserId | None) -> None:
        self._queues.pop(queue, None)
        if not user_id:
            return
        user_queues = self._queues_by_user.get(str(user_id))
        if user_queues is None:
            return
        user_queues.discard(queue)
        if not user_queues:
            del self._queues_by_user[str(user_id)]

    def _ensure_reader(self) -> None:
        # Started on the first stream, not at construction: the worker and the
        # scheduler only publish, and must not hold a pub/sub connection.
        if self._reader is None or self._reader.done():
            self._reader = asyncio.create_task(self._read(), name="sse-reader")

    async def _read(self) -> None:
        failures = 0
        while True:
            pubsub = self.redis.pubsub()
            try:
                await pubsub.subscribe(BROADCAST_CHANNEL)
                await pubsub.psubscribe(f"{USER_CHANNEL_PREFIX}*")
                failures = 0
                await self._pump(pubsub)
            except Exception:
                logger.warning(
                    "Realtime subscription lost; reconnecting", exc_info=True
                )
            finally:
                # The socket may already be gone; nothing to act on here.
                with contextlib.suppress(Exception):
                    await pubsub.aclose()
            failures += 1
            await asyncio.sleep(_reconnect_delay(failures))

    async def _pump(self, pubsub: PubSub) -> None:
        awaiting_pong = False
        while True:
            # Subscribe confirmations are kept, not ignored: redis-py returns
            # None for an ignored message too, which would read as a timeout.
            message = await pubsub.get_message(timeout=_HEALTH_CHECK_INTERVAL_SECONDS)
            if message is None:
                if awaiting_pong:
                    msg = "Valkey did not answer a ping on the realtime subscription"
                    raise ConnectionError(msg)
                await pubsub.ping()
                awaiting_pong = True
                continue
            # Any traffic, a pong or a confirmation included, proves the socket
            # is alive.
            awaiting_pong = False
            if message["type"] in {"message", "pmessage"}:
                self._dispatch(message)

    def _dispatch(self, message: dict[str, Any]) -> None:
        channel: str = message["channel"]
        if channel == BROADCAST_CHANNEL:
            targets = dict(self._queues)
        else:
            user_id = channel.removeprefix(USER_CHANNEL_PREFIX)
            user_queues = self._queues_by_user.get(user_id, set())
            targets = {queue: self._queues[queue] for queue in user_queues}
        if not targets:
            return
        try:
            sse_message = self.retort.load(json.loads(message["data"]), SSEMessage)
        except Exception:
            # One malformed message must not take the reader, and with it every
            # open stream, down.
            logger.exception("Dropped an undecodable realtime message")
            return
        for queue, queue_user_id in targets.items():
            _offer(queue, sse_message, user_id=queue_user_id)
