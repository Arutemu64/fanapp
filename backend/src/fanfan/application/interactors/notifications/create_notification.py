import logging
from dataclasses import replace

from pydantic import BaseModel

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.html_sanitizer import HtmlSanitizer
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.notification import NewNotification, Notification
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)


class CreateNotificationInput(BaseModel):
    notification: NewNotification


class CreateNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        html_sanitizer: HtmlSanitizer,
        realtime_gateway: RealtimeGateway,
        uow: UnitOfWork,
    ) -> None:
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.html_sanitizer = html_sanitizer
        self.realtime_gateway = realtime_gateway
        self.uow = uow

    def _to_model(self, notification: NewNotification) -> Notification:
        # Sanitize the body to the canonical safe HTML subset here, the single
        # point every notification passes through before it is stored and then
        # fanned out to the web UI, Telegram and push.
        return Notification.create(
            replace(notification, body=self.html_sanitizer.sanitize(notification.body))
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
        mailing = None
        if mailing_id is not None:
            mailing = await self.mailing_gateway.get(mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
        inserted = await self.notification_gateway.add(notification)
        # Only count a genuinely new notification: a rerun
        # CreateNotificationCommand repeats this with the same id, and the gateway
        # upsert above no-ops it, so incrementing here as well would drift
        # sent_count above the true delivered count. The same check keeps the
        # rerun from queuing the channel sends again (NotificationCreated is
        # queued only for a new row).
        if inserted and mailing is not None:
            sent_count, total_count = await self.mailing_gateway.increment_sent(
                mailing_id=mailing.id
            )
            # The mailing row is still locked (get above took FOR UPDATE), so the
            # increment and the aggregate's completion decision are serialized
            # across the concurrent fan-out. The rule lives on the aggregate;
            # persist only when this delivery is the one that finished it.
            if mailing.register_delivery(
                sent_count=sent_count, total_count=total_count
            ):
                await self.mailing_gateway.save(mailing)
        await self.uow.commit()
        await self._publish_realtime(notification)
        return notification.id

    async def _publish_realtime(self, notification: Notification) -> None:
        # After commit, so a toast never shows a notification that rolled back.
        # Best-effort: the notification is stored and the feed shows it on the
        # next load, so a failure here is logged, not raised — raising would
        # fail the job and rerun a notification that is already stored. A rerun
        # publishes again: a repeated toast beats a lost one.
        try:
            dto = await self.notification_gateway.read_realtime_notification(
                notification.id
            )
            if dto is None:
                # Deleted between commit and read, e.g. its mailing was cancelled.
                logger.warning(
                    "Notification gone before realtime delivery",
                    extra={"notification_id": str(notification.id)},
                )
                return
            await self.realtime_gateway.publish(
                SSEMessage(
                    SSEEventName.NOTIFICATION_CREATED,
                    data=dto.model_dump(mode="json"),
                ),
                user_id=notification.user_id,
            )
        except Exception:
            logger.exception(
                "Failed to publish realtime notification",
                extra={"notification_id": str(notification.id)},
            )
