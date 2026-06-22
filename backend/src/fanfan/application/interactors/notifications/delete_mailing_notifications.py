import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


class DeleteMailingNotificationsInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingNotifications:
    def __init__(
        self,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
    ):
        self.notification_gateway = notification_gateway
        self.uow = uow

    async def __call__(self, data: DeleteMailingNotificationsInput) -> None:
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.uow.commit()
        logger.info(
            "Mailing notifications deleted",
            extra={"mailing_id": str(data.mailing_id)},
        )
        return
