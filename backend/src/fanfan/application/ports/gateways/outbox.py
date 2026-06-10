from typing import Protocol
from uuid import UUID

from fanfan.application.dto.outbox import OutboxMessage


class OutboxGateway(Protocol):
    async def fetch_unpublished(self, limit: int) -> list[OutboxMessage]:
        """Lock and return the oldest undelivered rows (FOR UPDATE SKIP LOCKED).

        Locking lets several relay workers run safely without double-sending;
        the locks are released when the relay commits after marking the rows.
        """
        ...

    async def mark_published(self, ids: list[UUID]) -> None: ...

    async def delete_published_before(self, days: int) -> int:
        """Delete delivered rows older than ``days``; return the row count."""
        ...
