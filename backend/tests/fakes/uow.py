from collections.abc import Iterable

from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import AppEvent
from fanfan.core.models.base import AggregateRoot


class FakeUnitOfWork(UnitOfWork):
    """Keeps recorded events in memory and moves them to ``committed`` on commit."""

    def __init__(self) -> None:
        self._pending: list[AppEvent] = []
        self.committed: list[AppEvent] = []

    def register(self, entity: AggregateRoot) -> None:
        self._pending.extend(entity.pull_events())

    def record_events(self, events: Iterable[AppEvent]) -> None:
        self._pending.extend(events)

    async def commit(self) -> None:
        self.committed.extend(self._pending)
        self._pending.clear()

    async def rollback(self) -> None:
        self._pending.clear()
