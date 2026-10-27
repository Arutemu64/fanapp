from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.adapters.debug.tracing import current_trace_headers
from fanfan.application.commands.base import Command
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import Message
from fanfan.core.models.base import AggregateRoot


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._tracked: dict[int, AggregateRoot] = {}
        self._commands: list[Command] = []

    def register(self, entity: AggregateRoot) -> None:
        self._tracked[id(entity)] = entity

    def enqueue(self, command: Command) -> None:
        self._commands.append(command)

    async def commit(self) -> None:
        self._store_messages()
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
        self._tracked.clear()
        self._commands.clear()

    async def flush(self) -> None:
        await self.session.flush()

    def _store_messages(self) -> None:
        messages: list[Message] = []
        for entity in self._tracked.values():
            messages.extend(entity.pull_events())
        messages.extend(self._commands)
        self._tracked.clear()
        self._commands.clear()
        trace_headers = current_trace_headers() or None
        for message in messages:
            self.session.add(
                OutboxEventORM(
                    subject=message.subject,
                    payload=message.model_dump(mode="json"),
                    trace_headers=trace_headers,
                )
            )
