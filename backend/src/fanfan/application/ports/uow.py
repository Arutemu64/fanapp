from typing import Protocol

from fanfan.core.models.base import AggregateRoot


class UnitOfWork(Protocol):
    """Transaction boundary that also dispatches recorded domain events.

    Repositories call ``register`` for every aggregate they add or load, so the
    interactor never has to pull and publish events by hand. On ``commit`` the
    transaction is persisted first, then the domain events recorded on those
    aggregates are published.
    """

    def register(self, entity: AggregateRoot) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
