from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.html_sanitizer import HtmlSanitizer
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
        html_sanitizer: HtmlSanitizer,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.html_sanitizer = html_sanitizer
        self.uow = uow

    def _to_model(self, notification: NewNotification) -> Notification:
        # Sanitize the body to the canonical safe HTML subset here, the single
        # point every notification passes through before it is stored and then
        # fanned out to the web UI, Telegram and push.
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=self.html_sanitizer.sanitize(notification.body),
            type=notification.type,
            path=notification.path,
            mailing_id=notification.mailing_id,
            seen_at=None,
        )

    async def __call__(self, data: CreateNotificationInput) -> NotificationId:
        mailing_id = data.notification.mailing_id
        notification = self._to_model(data.notification)
        # Lock the mailing row (SELECT ... FOR UPDATE) before inserting the
        # notification, not after. The INSERT takes a FOR KEY SHARE lock on the
        # referenced mailing row via its foreign key; if two consumers fanning
        # out the same mailing both insert first and then try to upgrade to
        # FOR UPDATE, they hold each other's shared lock and deadlock. Taking
        # the exclusive lock first gives every consumer the same one-directional
        # lock order, so they serialize on the mailing instead.
        if mailing_id is not None:
            mailing = await self.mailing_gateway.get(mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
            await self.mailing_gateway.increment_sent(mailing_id=mailing_id)
        await self.notification_gateway.add(notification)
        await self.uow.commit()
        return notification.id
