from uuid import uuid7

from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


class MailingService:
    def __init__(self, mailing_gateway: MailingRepository):
        self.mailing_gateway = mailing_gateway

    async def create_new_mailing(self, total_count: int, by_user_id: UserId) -> Mailing:
        mailing = Mailing(
            id=MailingId(uuid7()),
            status=MailingStatus.PENDING,
            by_user_id=by_user_id,
            sent_count=0,
            total_count=total_count,
        )
        await self.mailing_gateway.add(mailing)
        return mailing
