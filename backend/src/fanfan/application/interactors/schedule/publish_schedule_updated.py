from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.realtime_gateway import RealtimeGateway


class PublishScheduleUpdated:
    """Send ``schedule_updated`` to every screen as a live update."""

    def __init__(self, realtime: RealtimeGateway) -> None:
        self.realtime = realtime

    async def __call__(self) -> None:
        await self.realtime.publish(SSEMessage(SSEEventName.SCHEDULE_UPDATED))
