from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent


class FakeEventBroker(EventBroker):
    def __init__(self):
        self.published_events: list[AppEvent] = []

    async def publish(self, event: AppEvent) -> None:
        self.published_events.append(event)
