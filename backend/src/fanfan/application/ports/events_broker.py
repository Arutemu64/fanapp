from abc import abstractmethod
from typing import Protocol

from fanfan.core.events.base import AppEvent


class EventBroker(Protocol):
    @abstractmethod
    async def publish(self, event: AppEvent) -> None:
        raise NotImplementedError
