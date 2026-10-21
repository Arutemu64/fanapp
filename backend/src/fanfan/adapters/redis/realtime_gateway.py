import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from adaptix import Retort
from redis.asyncio import Redis
from redis.exceptions import RedisError

from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

# Cap per-connection buffering so a slow/stuck SSE client cannot grow memory
# without bound. On overflow we drop the oldest message to favour freshness.
SSE_QUEUE_MAXSIZE = 100

_BROADCAST_CHANNEL = "sse:broadcast"
_USER_CHANNEL_PREFIX = "sse:user:"
_ALL_CHANNELS = "sse:*"

# Pause before resubscribing once redis-py's own reconnect retries give up, so
# a Redis outage costs a log line every few seconds, not a hot loop.
_RESUBSCRIBE_DELAY_SECONDS = 5.0


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


class RedisRealtimeGateway(RealtimeGateway):
    """Fans SSE messages out to every API process over Redis pub/sub.

    Pub/sub is fire-and-forget: a process not subscribed at publish time never
    sees the message. That fits SSE, which carries no committed state — a client
    that missed a live update refetches when it reconnects.
    https://redis.io/docs/latest/develop/use-cases/pub-sub/

    Each process holds one pattern subscription and routes messages to its open
    streams itself. A subscription per stream would pin a Redis connection per
    viewer, since a redis-py PubSub keeps its own connection. Relies on APP scope
    (main/ioc/redis.py): one gateway per process.
    """

    def __init__(self, redis: Redis, retort: Retort) -> None:
        self.redis = redis
        self.retort = retort
        # Queues map to their stream's user only for the overflow log.
        self._queues: dict[asyncio.Queue[SSEMessage], UserId | None] = {}
        self._queues_by_user: dict[UserId, set[asyncio.Queue[SSEMessage]]] = {}
        self._listener: asyncio.Task[None] | None = None
        self._subscribed = asyncio.Event()

    async def publish(self, message: SSEMessage, user_id: UserId | None = None) -> None:
        channel = _BROADCAST_CHANNEL
        if user_id:
            channel = f"{_USER_CHANNEL_PREFIX}{user_id}"
        await self.redis.publish(channel, json.dumps(self.retort.dump(message)))

    def subscribe(self, user_id: UserId | None = None) -> AsyncIterator[SSEMessage]:
        async def iterator() -> AsyncIterator[SSEMessage]:
            queue: asyncio.Queue[SSEMessage] = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)
            self._attach(queue, user_id)
            try:
                self._ensure_listener()
                await self._subscribed.wait()
                logger.info(
                    "Realtime subscriptions attached",
                    extra={
                        "authenticated": user_id is not None,
                        "user_id": str(user_id) if user_id else None,
                    },
                )
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
        if self._listener is None:
            return
        self._listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._listener

    def _attach(self, queue: asyncio.Queue[SSEMessage], user_id: UserId | None) -> None:
        self._queues[queue] = user_id
        if user_id:
            self._queues_by_user.setdefault(user_id, set()).add(queue)

    def _detach(self, queue: asyncio.Queue[SSEMessage], user_id: UserId | None) -> None:
        self._queues.pop(queue, None)
        if not user_id:
            return
        user_queues = self._queues_by_user.get(user_id)
        if user_queues is None:
            return
        user_queues.discard(queue)
        if not user_queues:
            del self._queues_by_user[user_id]

    def _ensure_listener(self) -> None:
        # Started by the first stream and kept for the life of the process: an
        # idle subscription costs one connection, and a worker that only
        # publishes never starts it.
        if self._listener is None or self._listener.done():
            self._listener = asyncio.create_task(self._listen(), name="sse-listener")

    async def _listen(self) -> None:
        while True:
            pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
            try:
                await pubsub.psubscribe(_ALL_CHANNELS)
                self._subscribed.set()
                # redis-py reconnects and resubscribes on its own; it raises
                # here only once its retries are spent.
                async for raw in pubsub.listen():
                    self._route_safely(raw["channel"], raw["data"])
            except RedisError:
                logger.warning("SSE subscription lost, resubscribing", exc_info=True)
            finally:
                await pubsub.aclose()
            await asyncio.sleep(_RESUBSCRIBE_DELAY_SECONDS)

    def _route_safely(self, channel: str, data: str) -> None:
        # One malformed message must not end the subscription for every stream.
        try:
            self._route(channel, data)
        except Exception:
            logger.exception(
                "Could not route an SSE message", extra={"channel": channel}
            )

    def _route(self, channel: str, data: str) -> None:
        message = self.retort.load(json.loads(data), SSEMessage)
        if channel == _BROADCAST_CHANNEL:
            for queue, user_id in self._queues.items():
                _offer(queue, message, user_id=user_id)
            return
        if not channel.startswith(_USER_CHANNEL_PREFIX):
            return
        user_id = UserId(UUID(channel.removeprefix(_USER_CHANNEL_PREFIX)))
        for queue in self._queues_by_user.get(user_id, ()):
            _offer(queue, message, user_id=user_id)
