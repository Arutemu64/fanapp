import logging

from pydantic import BaseModel

from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


class DeleteMailingMessagesInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingMessages:
    def __init__(
        self,
        notification_repo: NotificationRepository,
        trx: TransactionManager,
    ):
        self.notification_gateway = notification_repo
        self.trx = trx

    async def __call__(self, data: DeleteMailingMessagesInput) -> None:
        # TODO try to delete as much as possible
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.trx.commit()
        logger.info("Mailing %s notifications were deleted", data.mailing_id)
        return
