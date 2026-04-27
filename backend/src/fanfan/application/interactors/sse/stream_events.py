import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from fanfan.application.dto.realtime import SSE_CONNECTED_EVENT, SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.services.current_user import CurrentUserProvider

logger = logging.getLogger(__name__)


class StreamEvents:
    def __init__(
        self,
        realtime_gateway: RealtimeGateway,
        current_user_provider: CurrentUserProvider,
    ):
        self.realtime_gateway = realtime_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> AsyncGenerator[SSEMessage]:
        user_id = await self.current_user_provider.get_user_id()
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
