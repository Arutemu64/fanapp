from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import CursorResult, and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import NotificationORM
from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


def _from_model(model: Notification) -> NotificationORM:
    return NotificationORM(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        body=model.body,
        type=model.type,
        path=model.path,
        mailing_id=model.mailing_id,
        seen_at=model.seen_at,
    )


def _to_model(orm: NotificationORM) -> Notification:
    return Notification(
        id=NotificationId(orm.id),
        user_id=UserId(orm.user_id),
        title=orm.title,
        body=orm.body,
        type=NotificationType(orm.type),
        path=orm.path,
        mailing_id=MailingId(orm.mailing_id) if orm.mailing_id is not None else None,
        seen_at=orm.seen_at,
    )


def _parse_dto(orm: NotificationORM) -> NotificationDTO:
    return NotificationDTO(
        id=NotificationId(orm.id),
        user_id=UserId(orm.user_id),
        title=orm.title,
        body=orm.body,
        type=NotificationType(orm.type),
        path=orm.path,
        mailing_id=MailingId(orm.mailing_id) if orm.mailing_id is not None else None,
        created_at=orm.created_at,
        seen_at=orm.seen_at,
    )


class SqlNotificationGateway(NotificationGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, notification: Notification) -> None:
        notification_orm = _from_model(notification)
        self.session.add(notification_orm)
        await self.session.flush([notification_orm])

    async def get(self, notification_id: NotificationId) -> Notification | None:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.id == notification_id)
            .with_for_update()
        )
        notification_orm = await self.session.scalar(stmt)
        return _to_model(notification_orm) if notification_orm else None

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

    async def mark_read_for_user(
        self,
        user_id: UserId,
        notification_ids: list[NotificationId],
        timestamp: datetime,
    ) -> None:
        stmt = (
            update(NotificationORM)
            .where(
                and_(
                    NotificationORM.user_id == user_id,
                    NotificationORM.id.in_(notification_ids),
                    NotificationORM.seen_at.is_(None),
                )
            )
            .values({"seen_at": timestamp})
        )
        await self.session.execute(stmt)

    async def count_unread_for_user(self, user_id: UserId) -> int:
        stmt = select(func.count()).where(
            and_(
                NotificationORM.user_id == user_id,
                NotificationORM.seen_at.is_(None),
            )
        )
        return await self.session.scalar(stmt) or 0

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

    async def read_realtime_notification(
        self, notification_id: NotificationId
    ) -> NotificationDTO | None:
        stmt = select(NotificationORM).where(NotificationORM.id == notification_id)
        notification_orm = await self.session.scalar(stmt)
        return _parse_dto(notification_orm) if notification_orm else None

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
        return [_parse_dto(n) for n in notifications]
