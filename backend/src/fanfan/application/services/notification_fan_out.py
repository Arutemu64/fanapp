import itertools
import logging
from collections.abc import Sequence

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.html_sanitizer import HtmlSanitizer
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationCreated
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.notification import NewNotification, Notification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 500


class NotificationFanOut:
    """Store notifications and hand each one to the delivery channels.

    The one path every notification takes, so its body is sanitized in one
    place before it is stored and then sent to the web UI, Telegram, VK and
    push. Rerunnable: notification ids are deterministic per recipient, so a
    redelivered caller inserts nothing twice and finishes the mailing again; it
    does publish again, which the channels absorb (``NotificationCreated`` is
    deduplicated by JetStream, and a repeated toast beats a lost one).
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        html_sanitizer: HtmlSanitizer,
        realtime_gateway: RealtimeGateway,
        events_broker: EventBroker,
        uow: UnitOfWork,
    ) -> None:
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.html_sanitizer = html_sanitizer
        self.realtime_gateway = realtime_gateway
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(
        self,
        notifications: Sequence[NewNotification],
        *,
        mailing_id: MailingId | None = None,
    ) -> None:
        """Deliver every notification of ``mailing_id``, or mailing-less ones.

        The transaction that stores the last chunk finishes the mailing, so it
        is FINISHED exactly when every notification exists; an empty list
        finishes it at once.

        Raises ``MailingAlreadyCancelled`` once the mailing is cancelled; the
        chunks stored before that are removed by the cancellation itself.
        """
        if any(n.mailing_id != mailing_id for n in notifications):
            msg = "A fan-out delivers the notifications of one mailing"
            raise ValueError(msg)
        chunks = list(itertools.batched(notifications, _CHUNK_SIZE, strict=False))
        if not chunks:
            await self._store((), mailing_id, finish_with=0)
            return
        for chunk in chunks:
            finish_with = len(notifications) if chunk is chunks[-1] else None
            await self._store(chunk, mailing_id, finish_with=finish_with)
            ids = [notification.id for notification in chunk]
            await self._publish_realtime(ids)
            await self.events_broker.publish_many(
                [NotificationCreated(notification_id=id_) for id_ in ids]
            )

    def _to_model(self, notification: NewNotification) -> Notification:
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=self.html_sanitizer.sanitize(notification.body),
            type=notification.type,
            path=notification.path,
            mailing_id=notification.mailing_id,
            seen_at=None,
            event_id=notification.event_id,
        )

    async def _store(
        self,
        chunk: Sequence[NewNotification],
        mailing_id: MailingId | None,
        *,
        finish_with: int | None,
    ) -> None:
        mailing = None
        if mailing_id is not None:
            mailing = await self.mailing_gateway.get(mailing_id)
            if mailing is None:
                raise MailingNotFound
            mailing.ensure_active()
        await self.notification_gateway.add_many(
            [self._to_model(notification) for notification in chunk]
        )
        if mailing is not None and finish_with is not None:
            mailing.finish(finish_with)
            await self.mailing_gateway.save(mailing)
        await self.uow.commit()

    async def _publish_realtime(self, ids: Sequence[NotificationId]) -> None:
        try:
            dtos = await self.notification_gateway.read_realtime_notifications(ids)
            await self.uow.commit()
            for dto in dtos:
                await self.realtime_gateway.publish(
                    SSEMessage(
                        SSEEventName.NOTIFICATION_CREATED,
                        data=dto.model_dump(mode="json"),
                    ),
                    user_id=dto.user_id,
                )
        except Exception:
            logger.exception(
                "Failed to publish realtime notifications",
                extra={"notification_count": len(ids)},
            )
            await self.uow.rollback()
