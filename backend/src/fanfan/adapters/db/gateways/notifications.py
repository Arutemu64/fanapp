from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import CursorResult, and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.notification import NotificationMapper
from fanfan.adapters.db.models import NotificationORM
from fanfan.application.dto.notification import NotificationDTO, RealtimeNotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId


class SqlNotificationGateway(NotificationGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = NotificationMapper()

    async def add(self, notification: Notification) -> None:
        notification_orm = self.mapper.from_model(notification)
        self.session.add(notification_orm)
        await self.session.flush([notification_orm])

    async def get(self, notification_id: NotificationId) -> Notification | None:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.id == notification_id)
            .with_for_update()
        )
        notification_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(notification_orm) if notification_orm else None

    async def mark_all_read_for_user(
        self, user_id: UserId, timestamp: datetime
    ) -> None:
        stmt = (
            update(NotificationORM)
            .where(
                and_(
                    NotificationORM.user_id == user_id,
                    NotificationORM.seen_at.is_(None),
                )
            )
            .values({"seen_at": timestamp})
        )
        await self.session.execute(stmt)

    async def delete_all_by_mailing_id(self, mailing_id: MailingId) -> None:
        stmt = delete(NotificationORM).where(NotificationORM.mailing_id == mailing_id)
        await self.session.execute(stmt)

    async def delete_created_before(self, days: int) -> int:
        cutoff = func.now() - timedelta(days=days)
        result = await self.session.execute(
            delete(NotificationORM).where(NotificationORM.created_at < cutoff)
        )
        # execute() is typed as Result, but a DELETE yields a CursorResult.
        return cast("CursorResult", result).rowcount

    # Read projections (return DTOs, not aggregates)
    async def read_realtime_notification(
        self, notification_id: NotificationId
    ) -> RealtimeNotificationDTO | None:
        stmt = select(NotificationORM).where(NotificationORM.id == notification_id)
        notification_orm = await self.session.scalar(stmt)
        return (
            self.mapper.parse_realtime_dto(notification_orm)
            if notification_orm
            else None
        )

    async def read_list_user_notifications(
        self, user_id: UserId, pagination: Pagination
    ) -> list[NotificationDTO]:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.user_id == user_id)
            .order_by(NotificationORM.created_at.desc())
        )
        stmt = stmt.limit(pagination.limit).offset(pagination.offset)
        notifications = await self.session.scalars(stmt)
        return [self.mapper.parse_dto(n) for n in notifications]
