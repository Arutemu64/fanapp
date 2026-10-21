from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import JobORM
from fanfan.adapters.debug.tracing import current_trace_headers
from fanfan.application.dto.jobs import EventRoutes
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import AppEvent
from fanfan.core.models.base import AggregateRoot


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession, routes: EventRoutes) -> None:
        self.session = session
        self.routes = routes
        # Aggregates touched in this unit of work, keyed by object identity so
        # the same instance is never tracked (and stored) twice.
        self._tracked: dict[int, AggregateRoot] = {}
        self._events: list[AppEvent] = []

    def register(self, entity: AggregateRoot) -> None:
        self._tracked[id(entity)] = entity

    def record_events(self, events: Iterable[AppEvent]) -> None:
        self._events.extend(events)

    async def commit(self) -> None:
        # Store events as jobs in the same transaction as the aggregate change,
        # so the write and its jobs are durable together or not at all
        # (transactional outbox).
        self._store_events()
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
        # Drop events recorded for a transaction that never happened.
        self._tracked.clear()
        self._events.clear()

    async def flush(self) -> None:
        await self.session.flush()

    def _store_events(self) -> None:
        events = self._events
        self._events = []
        for entity in self._tracked.values():
            events.extend(entity.pull_events())
        self._tracked.clear()
        trace_headers = current_trace_headers() or None
        for event in events:
            payload = event.model_dump(mode="json")
            # One job per handler, so each retries on its own: a failing VK
            # send must not resend the Telegram one that already went out.
            for name in self.routes.jobs_for(event):
                self.session.add(
                    JobORM(name=name, payload=payload, trace_headers=trace_headers)
                )
