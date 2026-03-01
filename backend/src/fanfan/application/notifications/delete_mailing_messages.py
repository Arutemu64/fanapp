import logging
from dataclasses import dataclass

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DeleteMailingMessagesDTO:
    mailing_id: MailingId


class DeleteMailingMessages:
    def __init__(
        self,
        mailin_gateway: MailingGateway,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailin_gateway
        self.uow = uow

    async def __call__(self, data: DeleteMailingMessagesDTO):
        # TODO try to delete as much as possible
        async with self.uow:
            mailing = await self.mailing_gateway.get_mailing(data.mailing_id, lock=True)
            await self.mailing_gateway.delete_mailing(mailing)
            await self.uow.commit()
            logger.info("Mailing %s was cancelled", data.mailing_id)
            return
