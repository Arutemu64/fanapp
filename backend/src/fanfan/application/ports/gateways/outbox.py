from datetime import timedelta
from typing import Protocol
from uuid import UUID

from fanfan.application.dto.outbox import OutboxMessage


class OutboxGateway(Protocol):
    async def fetch_unpublished(self, limit: int) -> list[OutboxMessage]:
        """Lock and return the oldest undelivered rows (FOR UPDATE SKIP LOCKED).

        Rows whose retry is not yet due (see ``record_failed_attempt``) are
        skipped. Locking lets several relay workers run safely without
        double-sending; the locks are released when the relay commits after
        marking the rows.
        """
        ...

    async def mark_published(self, ids: list[UUID]) -> None: ...

    async def record_failed_attempt(
        self, message_id: UUID, error: str, retry_in: timedelta
    ) -> None:
        """Count a failed publish and hold the row back for ``retry_in``."""
        ...

    async def delete_published_before(self, days: int) -> int:
        """Delete delivered rows older than ``days``; return the row count."""
        ...
