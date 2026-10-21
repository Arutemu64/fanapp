from typing import Protocol

from fanfan.application.commands.base import Command
from fanfan.core.models.base import AggregateRoot


class UnitOfWork(Protocol):
    """Transaction boundary that also captures outgoing messages.

    Repositories call ``register`` for every aggregate they add or load, so the
    interactor never has to pull and publish events by hand. On ``commit`` the
    domain events recorded on those aggregates, and the commands passed to
    ``enqueue``, are written to the transactional outbox in the same
    transaction; the relay delivers them to NATS afterwards.
    """

    def register(self, entity: AggregateRoot) -> None: ...
    def enqueue(self, command: Command) -> None:
        """Send ``command`` once this transaction commits, and never if it
        rolls back — the outbox guarantee, without recording an instruction on
        an aggregate as if it were a fact (ADR-0040)."""
        ...

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
