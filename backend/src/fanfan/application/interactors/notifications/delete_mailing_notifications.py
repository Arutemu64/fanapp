import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


class DeleteMailingNotificationsInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingNotifications:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
    ) -> None:
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.uow = uow

    async def __call__(self, data: DeleteMailingNotificationsInput) -> None:
        mailing = await self.mailing_gateway.get(data.mailing_id)
        if mailing is not None:
            mailing.confirm_cancelled()
            await self.mailing_gateway.save(mailing)
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.uow.commit()
        logger.info(
            "Mailing cancelled and notifications deleted",
            extra={"mailing_id": str(data.mailing_id)},
        )
