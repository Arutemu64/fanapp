from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.notification import NewNotification, Notification
from fanfan.core.vo.notification import NotificationId


class CreateNotificationInput(BaseModel):
    notification: NewNotification


class CreateNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.uow = uow

    @staticmethod
    def _to_model(notification: NewNotification) -> Notification:
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            type=notification.type,
            mailing_id=notification.mailing_id,
            seen_at=None,
        )

    async def __call__(self, data: CreateNotificationInput) -> NotificationId:
        mailing_id = data.notification.mailing_id
        notification = self._to_model(data.notification)
        await self.notification_gateway.add(notification)
        if mailing_id is not None:
            mailing = await self.mailing_gateway.get(mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
            await self.mailing_gateway.increment_sent(mailing_id=mailing_id)
        await self.uow.commit()
        return notification.id
