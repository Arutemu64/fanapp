import logging
from dataclasses import dataclass

from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DeleteMailingMessagesDTO:
    mailing_id: MailingId


class DeleteMailingMessages:
    def __init__(
        self,
        notification_gateway: NotificationGateway,
        uow: UnitOfWork,
    ):
        self.notification_gateway = notification_gateway
        self.uow = uow

    async def __call__(self, data: DeleteMailingMessagesDTO):
        # TODO try to delete as much as possible
        async with self.uow:
            await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
            await self.uow.commit()
            logger.info("Mailing %s notifications were deleted", data.mailing_id)
            return
