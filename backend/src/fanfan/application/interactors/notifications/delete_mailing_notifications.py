import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId, MailingStatus

logger = logging.getLogger(__name__)


class DeleteMailingNotificationsInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingNotifications:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.uow = uow

    async def __call__(self, data: DeleteMailingNotificationsInput) -> None:
        # Reaction to MailingCancelled (from a broadcast cancel or a schedule
        # undo). Mark the mailing CANCELLED so ensure_active() rejects any
        # still-queued sends, then drop the undelivered notifications. Both are
        # idempotent, which matters under at-least-once redelivery. A delivered
        # push/Telegram/VK message is not recalled — it cannot be.
        await self.mailing_gateway.set_status(
            mailing_id=data.mailing_id, status=MailingStatus.CANCELLED
        )
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.uow.commit()
        logger.info(
            "Mailing cancelled and notifications deleted",
            extra={"mailing_id": str(data.mailing_id)},
        )
