from collections.abc import AsyncIterator
from typing import Protocol

from fanfan.application.dto.realtime import SSEMessage
from fanfan.core.vo.user import UserId


class RealtimeGateway(Protocol):
    async def publish(
        self, message: SSEMessage, user_id: UserId | None = None
    ) -> None: ...

    def subscribe(self, user_id: UserId | None = None) -> AsyncIterator[SSEMessage]: ...
