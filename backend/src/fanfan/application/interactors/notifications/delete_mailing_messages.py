import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


class DeleteMailingMessagesInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingMessages:
    def __init__(
        self,
        notification_repo: NotificationGateway,
        uow: UnitOfWork,
    ):
        self.notification_gateway = notification_repo
        self.uow = uow

    async def __call__(self, data: DeleteMailingMessagesInput) -> None:
        # TODO try to delete as much as possible
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.uow.commit()
        logger.info("Mailing %s notifications were deleted", data.mailing_id)
        return
