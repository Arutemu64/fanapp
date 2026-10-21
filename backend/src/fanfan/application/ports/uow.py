from collections.abc import Iterable
from typing import Protocol

from fanfan.core.events.base import AppEvent
from fanfan.core.models.base import AggregateRoot


class UnitOfWork(Protocol):
    """Transaction boundary that also captures recorded domain events.

    Repositories call ``register`` for every aggregate they add or load, so the
    interactor never has to pull and enqueue events by hand. On ``commit`` the
    domain events recorded on those aggregates — and any passed to
    ``record_events`` — are written to the jobs table in the same transaction,
    one job per handler of the event; the worker runs them afterwards.
    """

    def register(self, entity: AggregateRoot) -> None: ...

    def record_events(self, events: Iterable[AppEvent]) -> None:
        """Queue events that belong to no aggregate, such as a fan-out's.

        They are stored with the next ``commit`` and dropped by ``rollback``,
        exactly like an aggregate's events: nothing runs until the caller
        commits.
        """
        ...

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
