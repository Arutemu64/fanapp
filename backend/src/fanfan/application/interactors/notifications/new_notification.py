from pydantic import BaseModel

from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.mailing import MailingService
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationId


class NewNotificationInput(BaseModel):
    notification: NewNotificationDTO


class NewNotification:
    def __init__(
        self,
        mailing_repo: MailingRepository,
        notification_repo: NotificationRepository,
        notifications_service: MailingService,
        trx: TransactionManager,
    ):
        self.mailing_repo = mailing_repo
        self.notification_repo = notification_repo
        self.notifications_service = notifications_service
        self.trx = trx

    @staticmethod
    def _dto_to_model(notification: NewNotificationDTO) -> Notification:
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            type=notification.type,
            mailing_id=notification.mailing_id,
            seen_at=None,
        )

    async def __call__(self, data: NewNotificationInput) -> NotificationId:
        mailing_id = data.notification.mailing_id
        notification = self._dto_to_model(data.notification)
        await self.notification_repo.add(notification)
        if mailing_id is not None:
            await self.notifications_service.ensure_active_mailing(mailing_id)
            await self.mailing_repo.increment_sent(mailing_id=mailing_id)
        await self.trx.commit()
        return notification.id
