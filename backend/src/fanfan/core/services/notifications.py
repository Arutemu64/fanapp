from uuid import uuid7

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.core.exceptions.notifications import MailingCancelled
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.user import UserId


class NotificationService:
    def __init__(self, mailing_gateway: MailingGateway):
        self.mailing_gateway = mailing_gateway

    async def create_new_mailing(self, total_count: int, by_user_id: UserId) -> Mailing:
        mailing = Mailing(
            id=MailingId(uuid7()),
            status=MailingStatus.PENDING,
            by_user_id=by_user_id,
            sent_count=0,
            total_count=total_count,
        )
        return await self.mailing_gateway.add_mailing(mailing)

    async def ensure_active_mailing(self, mailing_id: MailingId) -> None:
        if mailing_id is None:
            return

        mailing = await self.mailing_gateway.get_mailing(mailing_id, lock=False)
        if mailing.status == MailingStatus.CANCELLED:
            raise MailingCancelled
