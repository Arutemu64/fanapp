from collections.abc import AsyncIterator
from typing import override

from fanfan.application.dto.realtime import SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.vo.user import UserId


class FakeRealtimeGateway(RealtimeGateway):
    """Records published SSE messages instead of going through NATS.

    ``subscribe`` returns an empty stream — real-time fan-out is not
    exercised in interactor tests, we only assert on what was published.
    """

    def __init__(self) -> None:
        self.published: list[tuple[UserId | None, SSEMessage]] = []

    @override
    async def publish(self, message: SSEMessage, user_id: UserId | None = None) -> None:
        self.published.append((user_id, message))

    @override
    def subscribe(
        self,
        user_id: UserId | None = None,
    ) -> AsyncIterator[SSEMessage]:
        return self._empty_stream()

    async def _empty_stream(self) -> AsyncIterator[SSEMessage]:
        return
        yield
