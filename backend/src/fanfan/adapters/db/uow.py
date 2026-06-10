from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.base import AggregateRoot


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        # Aggregates touched in this unit of work, keyed by object identity so
        # the same instance is never tracked (and stored) twice.
        self._tracked: dict[int, AggregateRoot] = {}

    def register(self, entity: AggregateRoot) -> None:
        self._tracked[id(entity)] = entity

    async def commit(self) -> None:
        # Store events in the same transaction as the aggregate change, so the
        # write and its events are durable together or not at all (outbox).
        self._store_events()
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
        # Drop events recorded for a transaction that never happened.
        self._tracked.clear()

    async def flush(self) -> None:
        await self.session.flush()

    def _store_events(self) -> None:
        tracked = list(self._tracked.values())
        self._tracked.clear()
        for entity in tracked:
            for event in entity.pull_events():
                self.session.add(
                    OutboxEventORM(
                        subject=event.subject,
                        payload=event.model_dump(mode="json"),
                    )
                )
