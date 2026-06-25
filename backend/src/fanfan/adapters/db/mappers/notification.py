from fanfan.adapters.db.models import NotificationORM
from fanfan.application.dto.notification import NotificationDTO
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId, NotificationType
from fanfan.core.vo.user import UserId


class NotificationMapper:
    @staticmethod
    def from_model(model: Notification) -> NotificationORM:
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

    @staticmethod
    def to_model(orm: NotificationORM) -> Notification:
        return Notification(
            id=NotificationId(orm.id),
            user_id=UserId(orm.user_id),
            title=orm.title,
            body=orm.body,
            type=NotificationType(orm.type),
            path=orm.path,
            mailing_id=MailingId(orm.mailing_id)
            if orm.mailing_id is not None
            else None,
            seen_at=orm.seen_at,
        )

    @staticmethod
    def parse_dto(orm: NotificationORM) -> NotificationDTO:
        return NotificationDTO(
            id=NotificationId(orm.id),
            user_id=UserId(orm.user_id),
            title=orm.title,
            body=orm.body,
            type=NotificationType(orm.type),
            path=orm.path,
            mailing_id=MailingId(orm.mailing_id)
            if orm.mailing_id is not None
            else None,
            created_at=orm.created_at,
            seen_at=orm.seen_at,
        )
