from typing import Protocol

from fanfan.core.models.base import AggregateRoot


class UnitOfWork(Protocol):
    """Transaction boundary that also captures recorded domain events.

    Repositories call ``register`` for every aggregate they add or load, so the
    interactor never has to pull and publish events by hand. On ``commit`` the
    domain events recorded on those aggregates are written to the transactional
    outbox in the same transaction; the relay delivers them to NATS afterwards.
    """

    def register(self, entity: AggregateRoot) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
