import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from adaptix import Retort
from nats.aio.msg import Msg

from fanfan.adapters.nats.factory import NATSClient
from fanfan.application.common.id_provider import IdProvider

logger = logging.getLogger(__name__)
SSE_CONNECTED_EVENT = "connected"


@dataclass(slots=True, frozen=True)
class SSEMessage:
    event_name: str
    data: dict | None = None


class StreamEvents:
    def __init__(self, nc: NATSClient, id_provider: IdProvider):
        self.nc = nc
        self.id_provider = id_provider
        self.retort = Retort()

    async def __call__(self) -> AsyncGenerator[SSEMessage]:
        queue: asyncio.Queue[SSEMessage] = asyncio.Queue()
        user_id = await self.id_provider.get_current_user_id()
        connection_id = uuid4().hex

        async def message_handler(msg: Msg):
            data = json.loads(msg.data.decode()) if msg.data else {}
            await queue.put(self.retort.load(data, SSEMessage))

        # Handle subscriptions
        subs = [await self.nc.subscribe("sse.broadcast.*", cb=message_handler)]
        if user_id:
            subs.append(
                await self.nc.subscribe(f"sse.user.{user_id}.*", cb=message_handler)
            )

        logger.info(
            "SSE subscriptions attached",
            extra={
                "connection_id": connection_id,
                "authenticated": user_id is not None,
                "user_id": str(user_id) if user_id else None,
                "subscriptions_count": len(subs),
            },
        )

        try:
            # Send a handshake immediately so the client can mark the stream as ready
            # before the first business event is published.
            handshake = SSEMessage(
                event_name=SSE_CONNECTED_EVENT,
                data={
                    "server_time": datetime.now(UTC).isoformat(),
                    "authenticated": user_id is not None,
                    "connection_id": connection_id,
                },
            )
            logger.info(
                "SSE handshake sent",
                extra={
                    "connection_id": connection_id,
                    "authenticated": user_id is not None,
                },
            )
            yield handshake

            while True:
                yield await asyncio.wait_for(queue.get(), timeout=None)
        finally:
            for sub in subs:
                await sub.unsubscribe()
            logger.info(
                "SSE subscriptions closed",
                extra={
                    "connection_id": connection_id,
                    "authenticated": user_id is not None,
                },
            )
