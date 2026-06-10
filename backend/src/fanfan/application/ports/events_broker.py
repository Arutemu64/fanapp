from typing import Protocol

from fanfan.core.events.base import AppEvent


class EventBroker(Protocol):
    async def publish(self, event: AppEvent) -> None: ...
