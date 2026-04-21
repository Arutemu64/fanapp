from fanfan.adapters.db.models import NotificationORM
from fanfan.application.dto.notification import NotificationDTO, RealtimeNotificationDTO
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType


class NotificationMapper:
    @staticmethod
    def from_model(model: Notification) -> NotificationORM:
        return NotificationORM(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            body=model.body,
            type=model.type,
            mailing_id=model.mailing_id,
            seen_at=model.seen_at,
        )

    @staticmethod
    def to_model(orm: NotificationORM) -> Notification:
        return Notification(
            id=orm.id,
            user_id=orm.user_id,
            title=orm.title,
            body=orm.body,
            type=NotificationType(orm.type),
            mailing_id=orm.mailing_id,
            seen_at=orm.seen_at,
        )

    @staticmethod
    def parse_dto(orm: NotificationORM) -> NotificationDTO:
        return NotificationDTO(
            id=orm.id,
            user_id=orm.user_id,
            title=orm.title,
            body=orm.body,
            type=NotificationType(orm.type),
            mailing_id=orm.mailing_id,
            created_at=orm.created_at,
            seen_at=orm.seen_at,
        )

    @staticmethod
    def parse_realtime_dto(orm: NotificationORM) -> RealtimeNotificationDTO:
        return RealtimeNotificationDTO(
            id=orm.id,
            user_id=orm.user_id,
            title=orm.title,
            body=orm.body,
            type=NotificationType(orm.type),
            mailing_id=orm.mailing_id,
            created_at=orm.created_at,
            seen_at=orm.seen_at,
        )
