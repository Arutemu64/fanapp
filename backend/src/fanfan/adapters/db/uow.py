from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.base import AggregateRoot


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession, events_broker: EventBroker) -> None:
        self.session = session
        self.events_broker = events_broker
        # Aggregates touched in this unit of work, keyed by object identity so
        # the same instance is never tracked (and dispatched) twice.
        self._tracked: dict[int, AggregateRoot] = {}

    def register(self, entity: AggregateRoot) -> None:
        self._tracked[id(entity)] = entity

    async def commit(self) -> None:
        await self.session.commit()
        # Publish domain events only after the transaction is durable.
        await self._dispatch_events()

    async def rollback(self) -> None:
        await self.session.rollback()
        # Drop events recorded for a transaction that never happened.
        self._tracked.clear()

    async def flush(self) -> None:
        await self.session.flush()

    async def _dispatch_events(self) -> None:
        tracked = list(self._tracked.values())
        self._tracked.clear()
        for entity in tracked:
            for event in entity.pull_events():
                await self.events_broker.publish(event)
