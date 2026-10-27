from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, and_, delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import NotificationORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.user import UserId


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
        created_at=orm.created_at,
        event_id=ScheduleEntryId(orm.event_id) if orm.event_id is not None else None,
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
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, notifications: Sequence[Notification]) -> int:
        if not notifications:
            return 0
        rows = [
            {
                "id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "body": notification.body,
                "type": notification.type,
                "path": notification.path,
                "mailing_id": notification.mailing_id,
                "seen_at": notification.seen_at,
                "event_id": notification.event_id,
            }
            for notification in notifications
        ]
        stmt = (
            pg_insert(NotificationORM)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(NotificationORM.id)
        )
        inserted = await self.session.scalars(stmt)
        return len(inserted.all())

    async def get(
        self, notification_id: NotificationId, *, lock: bool = True
    ) -> Notification | None:
        stmt = select(NotificationORM).where(NotificationORM.id == notification_id)
        if lock:
            stmt = stmt.with_for_update()
        notification_orm = await self.session.scalar(stmt)
        return _to_model(notification_orm) if notification_orm else None

    async def is_superseded(self, notification: Notification) -> bool:
        if notification.created_at is None:
            return False
        stmt = select(
            exists().where(
                NotificationORM.user_id == notification.user_id,
                NotificationORM.type == notification.type,
                NotificationORM.created_at > notification.created_at,
                NotificationORM.mailing_id.is_distinct_from(notification.mailing_id),
            )
        )
        return bool(await self.session.scalar(stmt))

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
        return cast("CursorResult[Any]", result).rowcount

    async def read_realtime_notifications(
        self, notification_ids: Sequence[NotificationId]
    ) -> list[NotificationDTO]:
        stmt = select(NotificationORM).where(NotificationORM.id.in_(notification_ids))
        notifications_orm = await self.session.scalars(stmt)
        return [_parse_dto(orm) for orm in notifications_orm]

    async def read_list_user_notifications(
        self, user_id: UserId, pagination: CursorPagination
    ) -> list[NotificationDTO]:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.user_id == user_id)
            .order_by(NotificationORM.created_at.desc(), NotificationORM.id.desc())
            .limit(pagination.fetch_limit)
        )
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(
                    NotificationORM.created_at, NotificationORM.id, pagination.after
                )
            )
        notifications = await self.session.scalars(stmt)
        return [_parse_dto(n) for n in notifications]
