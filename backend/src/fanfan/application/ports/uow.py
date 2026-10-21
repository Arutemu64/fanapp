from typing import Protocol

from fanfan.application.commands.base import Command
from fanfan.core.models.base import AggregateRoot


class UnitOfWork(Protocol):
    """Transaction boundary that also captures outgoing messages.

    Repositories call ``register`` for every aggregate they add or load, so the
    interactor never has to pull and publish events by hand. On ``commit`` the
    domain events recorded on those aggregates, and the commands passed to
    ``enqueue``, are written as background jobs in the same transaction, so a
    worker runs them once the change is durable and never if it rolls back
    (ADR-0041).
    """

    def register(self, entity: AggregateRoot) -> None: ...
    def enqueue(self, command: Command) -> None:
        """Queue ``command`` with this transaction: it runs once the transaction
        commits, and never if it rolls back — without recording an instruction
        on an aggregate as if it were a fact (ADR-0040)."""
        ...

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def flush(self) -> None: ...
