from faststream.nats import NatsBroker

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent


class NatsEventBroker(EventBroker):
    def __init__(self, broker: NatsBroker):
        self.broker = broker

    async def publish(self, event: AppEvent) -> None:
        await self.broker.publish(event, subject=event.subject)
