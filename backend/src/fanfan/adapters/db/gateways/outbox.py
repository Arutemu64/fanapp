from datetime import timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.application.dto.outbox import OutboxMessage
from fanfan.application.ports.gateways.outbox import OutboxGateway


class SqlOutboxGateway(OutboxGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_unpublished(self, limit: int) -> list[OutboxMessage]:
        rows = await self.session.scalars(
            select(OutboxEventORM)
            .where(OutboxEventORM.published_at.is_(None))
            .order_by(OutboxEventORM.created_at)
            .limit(limit)
            # SKIP LOCKED: a concurrent relay tick skips rows we already hold
            # instead of blocking, so ticks never double-send the same row.
            .with_for_update(skip_locked=True)
        )
        return [OutboxMessage.model_validate(row) for row in rows]

    async def mark_published(self, ids: list[UUID]) -> None:
        if not ids:
            return
        await self.session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.id.in_(ids))
            .values(published_at=func.now())
        )

    async def delete_published_before(self, days: int) -> int:
        cutoff = func.now() - timedelta(days=days)
        result = await self.session.execute(
            delete(OutboxEventORM).where(
                OutboxEventORM.published_at.is_not(None),
                OutboxEventORM.published_at < cutoff,
            )
        )
        # execute() is typed as Result, but a DELETE yields a CursorResult.
        return cast("CursorResult", result).rowcount
