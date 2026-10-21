from typing import Any, cast

from psycopg import AsyncConnection
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.procrastinate.job_queue import ProcrastinateJobQueue
from fanfan.application.commands.base import Command
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import Message
from fanfan.core.models.base import AggregateRoot


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession, job_queue: ProcrastinateJobQueue) -> None:
        self.session = session
        self.job_queue = job_queue
        # Aggregates touched in this unit of work, keyed by object identity so
        # the same instance is never tracked (and queued) twice.
        self._tracked: dict[int, AggregateRoot] = {}
        self._commands: list[Command] = []

    def register(self, entity: AggregateRoot) -> None:
        self._tracked[id(entity)] = entity

    def enqueue(self, command: Command) -> None:
        self._commands.append(command)

    async def commit(self) -> None:
        # Queue messages in the same transaction as the aggregate change, so the
        # write and its jobs are durable together or not at all — no dual write.
        messages = self._pull_messages()
        if messages:
            await self.job_queue.enqueue(await self._driver_connection(), messages)
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
        # Drop messages recorded for a transaction that never happened.
        self._tracked.clear()
        self._commands.clear()

    async def flush(self) -> None:
        await self.session.flush()

    def _pull_messages(self) -> list[Message]:
        messages: list[Message] = []
        for entity in self._tracked.values():
            messages.extend(entity.pull_events())
        messages.extend(self._commands)
        self._tracked.clear()
        self._commands.clear()
        return messages

    async def _driver_connection(self) -> AsyncConnection[Any]:
        # Procrastinate writes through psycopg, not SQLAlchemy, so it gets the
        # driver connection under the session's open transaction.
        # https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncConnection.get_raw_connection
        connection = await self.session.connection()
        raw = await connection.get_raw_connection()
        return cast("AsyncConnection[Any]", raw.driver_connection)
