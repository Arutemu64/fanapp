import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fanfan.application.dto.realtime import SSE_CONNECTED_EVENT, SSEMessage
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.realtime_gateway import RealtimeGateway

logger = logging.getLogger(__name__)


class StreamEvents:
    def __init__(self, realtime_gateway: RealtimeGateway, id_provider: IdProvider):
        self.realtime_gateway = realtime_gateway
        self.id_provider = id_provider

    async def __call__(self) -> AsyncGenerator[SSEMessage]:
        user_id = await self.id_provider.get_current_user_id()
        connection_id = uuid4().hex

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

        async for message in self.realtime_gateway.subscribe(user_id=user_id):
            yield message
