from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.notification import NotificationMapper
from fanfan.adapters.db.models import NotificationORM
from fanfan.core.dto.notification import NotificationDTO
from fanfan.core.dto.page import Pagination
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationId
from fanfan.core.vo.user import UserId


class NotificationGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = NotificationMapper()

    async def add_notification(self, notification: Notification) -> Notification:
        notification_orm = self.mapper.from_model(notification)
        self.session.add(notification_orm)
        await self.session.flush([notification_orm])
        return self.mapper.to_model(notification_orm)

    async def get_notification(
        self, notification_id: NotificationId
    ) -> Notification | None:
        stmt = select(NotificationORM).where(NotificationORM.id == notification_id)
        notification_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(notification_orm) if notification_orm else None

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
