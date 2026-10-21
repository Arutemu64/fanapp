from fanfan.application.commands.base import Command
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import Message
from fanfan.core.models.base import AggregateRoot


class FakeUnitOfWork(UnitOfWork):
    """Records what each commit would queue, for tests with no database."""

    def __init__(self) -> None:
        self.queued: list[Message] = []
        self._tracked: list[AggregateRoot] = []
        self._pending: list[Command] = []

    def register(self, entity: AggregateRoot) -> None:
        self._tracked.append(entity)

    def enqueue(self, command: Command) -> None:
        self._pending.append(command)

    async def commit(self) -> None:
        for entity in self._tracked:
            self.queued.extend(entity.pull_events())
        self.queued.extend(self._pending)
        self._tracked.clear()
        self._pending.clear()

    async def rollback(self) -> None:
        self._tracked.clear()
        self._pending.clear()

    async def flush(self) -> None: ...
