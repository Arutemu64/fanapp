import asyncio
import logging
from collections.abc import AsyncIterator
from typing import override

from nats.aio.msg import Msg
from nats.aio.subscription import Subscription
from pydantic import TypeAdapter

from fanfan.adapters.nats.factory import NATSClient
from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

_MESSAGE_ADAPTER = TypeAdapter(SSEMessage)

SSE_QUEUE_MAXSIZE = 100


def _decode(msg: Msg) -> SSEMessage:
    return _MESSAGE_ADAPTER.validate_json(msg.data, strict=True)


def _offer(
    queue: asyncio.Queue[SSEMessage], message: SSEMessage, user_id: UserId | None
) -> None:
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


class NatsRealtimeGateway(RealtimeGateway):
    def __init__(self, nc: NATSClient) -> None:
        self.nc = nc
        self._broadcast_queues: dict[asyncio.Queue[SSEMessage], UserId | None] = {}
        self._broadcast_subscription: Subscription | None = None
        self._broadcast_subscribe_lock = asyncio.Lock()

    @override
    async def publish(self, message: SSEMessage, user_id: UserId | None = None) -> None:
        payload = _MESSAGE_ADAPTER.dump_json(message)

        if user_id:
            await self.nc.publish(
                subject=f"sse.user.{user_id}.{message.event_name}",
                payload=payload,
            )
            return

        await self.nc.publish(
            subject=f"sse.broadcast.{message.event_name}",
            payload=payload,
        )

    async def _ensure_broadcast_subscription(self) -> None:
        async with self._broadcast_subscribe_lock:
            if self._broadcast_subscription is not None:
                return

            async def broadcast_handler(msg: Msg) -> None:
                message = _decode(msg)
                for queue, queue_user_id in self._broadcast_queues.items():
                    _offer(queue, message, user_id=queue_user_id)

            self._broadcast_subscription = await self.nc.subscribe(
                "sse.broadcast.*", cb=broadcast_handler
            )

    @override
    def subscribe(self, user_id: UserId | None = None) -> AsyncIterator[SSEMessage]:
        async def iterator() -> AsyncIterator[SSEMessage]:
            queue: asyncio.Queue[SSEMessage] = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)

            async def user_handler(msg: Msg) -> None:
                _offer(queue, _decode(msg), user_id=user_id)

            await self._ensure_broadcast_subscription()
            self._broadcast_queues[queue] = user_id
            user_subscription: Subscription | None = None
            try:
                if user_id:
                    user_subscription = await self.nc.subscribe(
                        f"sse.user.{user_id}.*", cb=user_handler
                    )

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
                self._broadcast_queues.pop(queue, None)
                if user_subscription is not None:
                    await user_subscription.unsubscribe()
                logger.info(
                    "Realtime subscriptions closed",
                    extra={
                        "authenticated": user_id is not None,
                        "user_id": str(user_id) if user_id else None,
                    },
                )

        return iterator()
