import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from adaptix import Retort
from nats.aio.msg import Msg

from fanfan.adapters.nats.factory import NATSClient
from fanfan.application.common.id_provider import IdProvider


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

        async def message_handler(msg: Msg):
            data = json.loads(msg.data.decode()) if msg.data else {}
            await queue.put(self.retort.load(data, SSEMessage))

        # Handle subscriptions
        subs = [await self.nc.subscribe("sse.broadcast.*", cb=message_handler)]
        if user_id:
            subs.append(
                await self.nc.subscribe(f"sse.user.{user_id}.*", cb=message_handler)
            )

        try:
            while True:
                yield await asyncio.wait_for(queue.get(), timeout=None)
        finally:
            for sub in subs:
                await sub.unsubscribe()
