from datetime import timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.application.dto.outbox import OutboxMessage
from fanfan.application.ports.gateways.outbox import OutboxGateway

_LAST_ERROR_MAX_CHARS = 2000


class SqlOutboxGateway(OutboxGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch_unpublished(self, limit: int) -> list[OutboxMessage]:
        rows = await self.session.scalars(
            select(OutboxEventORM)
            .where(
                OutboxEventORM.published_at.is_(None),
                or_(
                    OutboxEventORM.next_attempt_at.is_(None),
                    OutboxEventORM.next_attempt_at <= func.now(),
                ),
            )
            .order_by(OutboxEventORM.created_at, OutboxEventORM.id)
            .limit(limit)
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

    async def record_failed_attempt(
        self, message_id: UUID, error: str, retry_in: timedelta
    ) -> None:
        await self.session.execute(
            update(OutboxEventORM)
            .where(OutboxEventORM.id == message_id)
            .values(
                attempts=OutboxEventORM.attempts + 1,
                last_error=error[:_LAST_ERROR_MAX_CHARS],
                next_attempt_at=func.now() + retry_in,
            )
        )

    async def delete_published_before(self, days: int) -> int:
        cutoff = func.now() - timedelta(days=days)
        result = await self.session.execute(
            delete(OutboxEventORM).where(
                OutboxEventORM.published_at.is_not(None),
                OutboxEventORM.published_at < cutoff,
            )
        )
        return cast("CursorResult[Any]", result).rowcount
