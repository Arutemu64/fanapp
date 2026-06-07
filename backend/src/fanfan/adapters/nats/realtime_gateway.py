import asyncio
import json
import logging
from collections.abc import AsyncIterator

from adaptix import Retort
from nats.aio.msg import Msg

from fanfan.adapters.nats.factory import NATSClient
from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)

# Cap per-connection buffering so a slow/stuck SSE client cannot grow memory
# without bound. On overflow we drop the oldest message to favour freshness.
SSE_QUEUE_MAXSIZE = 100


class NatsRealtimeGateway(RealtimeGateway):
    def __init__(self, nc: NATSClient):
        self.nc = nc
        self.retort = Retort()

    async def publish(self, message: SSEMessage, user_id: UserId | None = None) -> None:
        payload = json.dumps(self.retort.dump(message)).encode()

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

    def subscribe(self, user_id: UserId | None = None) -> AsyncIterator[SSEMessage]:
        async def iterator() -> AsyncIterator[SSEMessage]:
            queue: asyncio.Queue[SSEMessage] = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)

            async def message_handler(msg: Msg) -> None:
                data = json.loads(msg.data.decode()) if msg.data else {}
                message = self.retort.load(data, SSEMessage)

                # Slow consumer: drop the oldest to make room for the newest.
                # No lock needed — asyncio runs this callback without interruption.
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

            subs = [await self.nc.subscribe("sse.broadcast.*", cb=message_handler)]
            if user_id:
                subs.append(
                    await self.nc.subscribe(f"sse.user.{user_id}.*", cb=message_handler)
                )

            logger.info(
                "Realtime subscriptions attached",
                extra={
                    "authenticated": user_id is not None,
                    "user_id": str(user_id) if user_id else None,
                    "subscriptions_count": len(subs),
                },
            )

            try:
                while True:
                    yield await queue.get()
            finally:
                for sub in subs:
                    await sub.unsubscribe()
                logger.info(
                    "Realtime subscriptions closed",
                    extra={
                        "authenticated": user_id is not None,
                        "user_id": str(user_id) if user_id else None,
                    },
                )

        return iterator()
