from faststream.nats import NatsBroker

from fanfan.application.sse.stream_events import SSEMessage
from fanfan.core.events.base import AppEvent
from fanfan.core.vo.user import UserId


class EventBroker:
    def __init__(self, broker: NatsBroker):
        self.broker = broker

    async def publish(self, event: AppEvent):
        await self.broker.publish(event, subject=event.subject)

    async def push_sse_message(
        self, message: SSEMessage, user_id: UserId | None = None
    ):
        if user_id:
            await self.broker.publish(
                message, subject=f"sse.user.{user_id}.{message.event_name}"
            )
        else:
            await self.broker.publish(
                message, subject=f"sse.broadcast.{message.event_name}"
            )
